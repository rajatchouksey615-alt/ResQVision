"""Human JWT serializers and the isolated machine-authentication interface."""

from dataclasses import dataclass
from hmac import compare_digest

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.module_loading import import_string
from rest_framework import serializers
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password

from common.domain.actors import MachineActor
from common.domain.authorization import AI_SERVICE_REF

from .exceptions import MachineAuthenticationUnavailable


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Authenticate using the canonical email address and generic failures."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=attrs.get("password", ""),
        )
        if user is None or not user.is_active:
            raise AuthenticationFailed("No active account found with the given credentials.")
        refresh = self.get_token(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RevocationAwareTokenRefreshSerializer(TokenRefreshSerializer):
    """Reject refresh tokens issued before the user's most recent password change."""

    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs["refresh"])
        except TokenError as exc:
            raise InvalidToken("Refresh token is invalid or expired.") from exc

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
        user = (
            get_user_model()
            .objects.filter(**{api_settings.USER_ID_FIELD: user_id}, is_active=True)
            .first()
        )
        if user is None:
            raise InvalidToken("Refresh token is invalid or expired.")
        if api_settings.CHECK_REVOKE_TOKEN and refresh.get(
            api_settings.REVOKE_TOKEN_CLAIM
        ) != get_md5_hash_password(user.password):
            raise InvalidToken("Refresh token is no longer valid.")
        return super().validate(attrs)


@dataclass(frozen=True, slots=True)
class VerifiedMachinePrincipal:
    """Value returned by a trusted, configured machine credential verifier."""

    service_ref: str


class AIServiceAuthentication(BaseAuthentication):
    """Delegate service credentials to a separately configured verifier."""

    def authenticate(self, request):
        path = getattr(settings, "AI_SERVICE_AUTHENTICATOR", None)
        if not path:
            raise MachineAuthenticationUnavailable()
        authenticator_type = import_string(path)
        result = authenticator_type().authenticate(request)
        if not isinstance(result, VerifiedMachinePrincipal):
            raise AuthenticationFailed("Machine credentials are invalid.")
        if result.service_ref != AI_SERVICE_REF:
            raise AuthenticationFailed("Machine credentials are invalid.")
        return result_to_actor(result)

    def authenticate_header(self, request):
        del request
        return "Machine"


def result_to_actor(principal: VerifiedMachinePrincipal):
    return (MachineActor(principal.service_ref), principal)


class TestMachineCredentialAuthenticator:
    """Explicit test-only authenticator; never configured by development settings."""

    def authenticate(self, request):
        if not getattr(settings, "TESTING", False):
            raise MachineAuthenticationUnavailable()
        scheme, separator, presented = request.headers.get("Authorization", "").partition(" ")
        expected = getattr(settings, "AI_TEST_MACHINE_TOKEN", "")
        if (
            scheme != "Machine"
            or not separator
            or not expected
            or not compare_digest(presented, expected)
        ):
            raise AuthenticationFailed("Machine credentials are invalid.")
        return VerifiedMachinePrincipal(AI_SERVICE_REF)
