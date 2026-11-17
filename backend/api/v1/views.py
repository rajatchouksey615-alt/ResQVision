"""Versioned DRF transport adapters over the existing domain services."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.detection.services import DetectionEventCommand, ingest_detection_event
from apps.incidents.services import get_incident
from apps.notifications.services import mark_notification_read
from apps.responses.services import (
    acknowledge_assignment,
    complete_assignment,
    mark_unable_to_respond,
    record_response_activity,
    start_response,
)
from common.domain.actors import HumanActor, MachineActor
from common.domain.authorization import AI_SERVICE_REF
from common.domain.exceptions import AuthorizationDenied, PolicyNotConfigured

from .actors import get_human_actor
from .authentication import AIServiceAuthentication, EmailTokenObtainPairSerializer
from .exceptions import EvidenceStorageUnavailable, MachineAuthenticationUnavailable
from .permissions import IsAuthenticatedHuman, IsAuthenticatedMachine
from .policies import AssignedIncidentReadPolicy
from .selectors import (
    active_memberships_for,
    visible_assignment_queryset,
    visible_incident_queryset,
    visible_notifications_queryset,
)
from .serializers import (
    AccountProfileSerializer,
    AssignmentCommandResponseSerializer,
    AssignmentCompleteSerializer,
    AssignmentStartSerializer,
    AssignmentSummarySerializer,
    AssignmentUnableSerializer,
    AuthenticatedUserSerializer,
    CommandIDSerializer,
    DetectionEventCreatedSerializer,
    DetectionEventInputSerializer,
    ErrorEnvelopeSerializer,
    IncidentStatusQuerySerializer,
    IncidentSummarySerializer,
    LogoutSerializer,
    NotificationCommandResponseSerializer,
    NotificationStatusQuerySerializer,
    NotificationSummarySerializer,
    PasswordChangeSerializer,
    ResponseActivityCommandResponseSerializer,
    ResponseActivityInputSerializer,
    ResponseActivitySerializer,
    SafeMembershipSerializer,
)
from .throttling import MachineScopedRateThrottle

API_ERROR_RESPONSES = {
    400: ErrorEnvelopeSerializer,
    401: ErrorEnvelopeSerializer,
    403: ErrorEnvelopeSerializer,
    404: ErrorEnvelopeSerializer,
    409: ErrorEnvelopeSerializer,
    413: ErrorEnvelopeSerializer,
    429: ErrorEnvelopeSerializer,
    503: ErrorEnvelopeSerializer,
}


class EmailTokenView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "login"


class RefreshTokenView(TokenRefreshView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "refresh"


class LogoutView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="auth_logout",
        request=LogoutSerializer,
        responses={204: None, **API_ERROR_RESPONSES},
        description="Blacklist this authenticated user's refresh session. Repeated logout is safe.",
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["refresh"]
        try:
            token = UntypedToken(raw_token)
        except TokenError as exc:
            raise InvalidToken("Refresh token is invalid or expired.") from exc
        if token.get("token_type") != "refresh":
            raise ValidationError({"refresh": "A refresh token is required."})
        if str(token.get(api_settings.USER_ID_CLAIM)) != str(request.user.pk):
            raise PermissionDenied("This refresh token belongs to another account.")
        if api_settings.CHECK_REVOKE_TOKEN and token.get(
            api_settings.REVOKE_TOKEN_CLAIM
        ) != get_md5_hash_password(request.user.password):
            raise InvalidToken("Refresh token is no longer valid.")

        jti = token.get(api_settings.JTI_CLAIM)
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

        if not BlacklistedToken.objects.filter(token__jti=jti).exists():
            try:
                with transaction.atomic():
                    RefreshToken(raw_token).blacklist()
            except TokenError as exc:
                if not BlacklistedToken.objects.filter(token__jti=jti).exists():
                    raise InvalidToken("Refresh token is invalid or expired.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuthenticatedUserView(APIView):
    permission_classes = (IsAuthenticatedHuman,)

    @extend_schema(
        operation_id="auth_me",
        responses={200: AuthenticatedUserSerializer, **API_ERROR_RESPONSES},
    )
    def get(self, request):
        actor = get_human_actor(request)
        return Response(AuthenticatedUserSerializer(actor.user).data)


class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="auth_password_change",
        request=PasswordChangeSerializer,
        responses={204: None, **API_ERROR_RESPONSES},
        description=(
            "Changing a password immediately revokes previously issued access and refresh tokens. "
            "The user must sign in again."
        ),
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_user_model().objects.filter(pk=request.user.pk, is_active=True).first()
        if user is None or not user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": "The current password is incorrect."})
        try:
            validate_password(serializer.validated_data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": exc.messages}) from exc
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountProfileView(APIView):
    permission_classes = (IsAuthenticatedHuman,)

    @extend_schema(
        operation_id="accounts_me_retrieve",
        responses={200: AccountProfileSerializer, **API_ERROR_RESPONSES},
    )
    def get(self, request):
        return Response(AccountProfileSerializer(get_human_actor(request).user).data)

    @extend_schema(
        operation_id="accounts_me_update",
        request=AccountProfileSerializer,
        responses={200: AccountProfileSerializer, **API_ERROR_RESPONSES},
    )
    def patch(self, request):
        user = get_human_actor(request).user
        serializer = AccountProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyMembershipsView(generics.ListAPIView):
    serializer_class = SafeMembershipSerializer
    permission_classes = (IsAuthenticatedHuman,)

    def get_queryset(self):
        return active_memberships_for(get_human_actor(self.request).user)


class OrganizationMembershipSummaryView(MyMembershipsView):
    def get_queryset(self):
        return super().get_queryset().filter(organization_id=self.kwargs["organization_id"])


class BlockedPolicyView(APIView):
    """Base for endpoints held behind an unresolved authorization decision."""

    permission_classes = (IsAuthenticatedHuman,)

    def _unavailable(self):
        raise PolicyNotConfigured("The operation remains disabled pending its approved policy.")


class BlockedSourceCollectionView(BlockedPolicyView):
    @extend_schema(operation_id="video_sources_list", responses={503: ErrorEnvelopeSerializer})
    def get(self, request):
        del request
        self._unavailable()

    @extend_schema(
        operation_id="video_sources_register",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request):
        del request
        self._unavailable()


class BlockedSourceDetailView(BlockedPolicyView):
    @extend_schema(operation_id="video_sources_retrieve", responses={503: ErrorEnvelopeSerializer})
    def get(self, request, source_id):
        del request, source_id
        self._unavailable()


class CandidateCollectionView(BlockedPolicyView):
    @extend_schema(operation_id="candidates_list", responses={503: ErrorEnvelopeSerializer})
    def get(self, request):
        del request
        self._unavailable()


class CandidateDetailView(BlockedPolicyView):
    @extend_schema(operation_id="candidates_retrieve", responses={503: ErrorEnvelopeSerializer})
    def get(self, request, candidate_id):
        del request, candidate_id
        self._unavailable()


class CandidateAssociateEventsView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="candidates_associate_events",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, candidate_id):
        del request, candidate_id
        self._unavailable()


class CandidateReviewView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="candidates_review",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, candidate_id):
        del request, candidate_id
        self._unavailable()


class BlockedIncidentResolveView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="incidents_resolve",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, incident_id):
        del request, incident_id
        self._unavailable()


class BlockedIncidentCloseView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="incidents_close",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, incident_id):
        del request, incident_id
        self._unavailable()


class BlockedAssignmentCancelView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_cancel",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, assignment_id):
        del request, assignment_id
        self._unavailable()


class BlockedAssignmentReassignView(BlockedPolicyView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_reassign",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, assignment_id):
        del request, assignment_id
        self._unavailable()


class EvidenceCollectionView(BlockedPolicyView):
    @extend_schema(operation_id="evidence_list", responses={503: ErrorEnvelopeSerializer})
    def get(self, request):
        del request
        self._unavailable()


class EvidenceDetailView(BlockedPolicyView):
    @extend_schema(operation_id="evidence_retrieve", responses={503: ErrorEnvelopeSerializer})
    def get(self, request, evidence_id):
        del request, evidence_id
        self._unavailable()


class IncidentLocationView(BlockedPolicyView):
    @extend_schema(operation_id="incident_locations_list", responses={503: ErrorEnvelopeSerializer})
    def get(self, request, incident_id):
        del request, incident_id
        self._unavailable()


class DetectionEventSubmissionView(APIView):
    authentication_classes = (AIServiceAuthentication,)
    permission_classes = (IsAuthenticatedMachine,)
    throttle_classes = (MachineScopedRateThrottle,)
    throttle_scope = "ai_ingestion"

    @extend_schema(
        operation_id="ai_detection_events_submit",
        auth=[],
        request=DetectionEventInputSerializer,
        responses={201: DetectionEventCreatedSerializer, **API_ERROR_RESPONSES},
        description=(
            "AI_SERVICE submission only. The route is unavailable until a formally approved "
            "machine authenticator and source authorization are configured."
        ),
    )
    def post(self, request):
        serializer = DetectionEventInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = request.user
        if not isinstance(actor, MachineActor) or actor.service_ref != AI_SERVICE_REF:
            raise MachineAuthenticationUnavailable()
        values = serializer.validated_data
        command = DetectionEventCommand(
            video_source_id=values["video_source_id"],
            external_event_id=values["external_event_id"],
            model_name=values["model_name"],
            model_version=values["model_version"],
            detected_at=values["detected_at"],
            processing_outcome=values["processing_outcome"],
            actor=actor,
            confidence=values.get("confidence"),
            payload_sha256=values.get("payload_sha256"),
            metadata_schema_version=values["metadata_schema_version"],
            auxiliary_metadata=values["auxiliary_metadata"],
        )
        event = ingest_detection_event(command)
        return Response(
            {"id": event.pk, "received_at": event.received_at},
            status=status.HTTP_201_CREATED,
        )


class IncidentListView(generics.ListAPIView):
    serializer_class = IncidentSummarySerializer
    permission_classes = (IsAuthenticatedHuman,)

    def get_queryset(self):
        params = IncidentStatusQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        queryset = visible_incident_queryset(get_human_actor(self.request).user)
        if status_filter := params.validated_data.get("status"):
            queryset = queryset.filter(status=status_filter)
        return queryset


class IncidentDetailView(APIView):
    permission_classes = (IsAuthenticatedHuman,)

    @extend_schema(
        operation_id="incidents_retrieve",
        responses={200: IncidentSummarySerializer, **API_ERROR_RESPONSES},
    )
    def get(self, request, incident_id):
        user = get_human_actor(request).user
        get_object_or_404(visible_incident_queryset(user), pk=incident_id)
        try:
            incident = get_incident(
                incident_id,
                actor=HumanActor(user),
                policy=AssignedIncidentReadPolicy(),
            )
        except AuthorizationDenied as exc:
            raise NotFound from exc
        return Response(IncidentSummarySerializer(incident).data)


class IncidentAssignmentsView(generics.ListAPIView):
    serializer_class = AssignmentSummarySerializer
    permission_classes = (IsAuthenticatedHuman,)

    def get_queryset(self):
        return visible_assignment_queryset(get_human_actor(self.request).user).filter(
            incident_id=self.kwargs["incident_id"]
        )


class AssignmentDetailView(APIView):
    permission_classes = (IsAuthenticatedHuman,)

    @extend_schema(
        operation_id="assignments_retrieve",
        responses={200: AssignmentSummarySerializer, **API_ERROR_RESPONSES},
    )
    def get(self, request, assignment_id):
        assignment = get_object_or_404(
            visible_assignment_queryset(get_human_actor(request).user), pk=assignment_id
        )
        return Response(AssignmentSummarySerializer(assignment).data)


def _assignment_for_request(request, assignment_id):
    return get_object_or_404(
        visible_assignment_queryset(get_human_actor(request).user), pk=assignment_id
    )


def _call_assigned_command(command, **kwargs):
    try:
        return command(**kwargs)
    except AuthorizationDenied as exc:
        raise NotFound from exc


def _assignment_command_response(result):
    return Response(
        {"data": AssignmentSummarySerializer(result.value).data, "replayed": result.replayed}
    )


class AssignmentAcknowledgeView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_acknowledge",
        request=CommandIDSerializer,
        responses={200: AssignmentCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, assignment_id):
        _assignment_for_request(request, assignment_id)
        serializer = CommandIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = _call_assigned_command(
            acknowledge_assignment,
            assignment_id=assignment_id,
            actor=get_human_actor(request),
            command_id=serializer.validated_data["command_id"],
        )
        return _assignment_command_response(result)


class AssignmentStartView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_start",
        request=AssignmentStartSerializer,
        responses={200: AssignmentCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, assignment_id):
        _assignment_for_request(request, assignment_id)
        serializer = AssignmentStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = _call_assigned_command(
            start_response,
            assignment_id=assignment_id,
            actor=get_human_actor(request),
            command_id=values["command_id"],
            details=values.get("details", ""),
        )
        return _assignment_command_response(result)


class AssignmentActivityView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_record_activity",
        request=ResponseActivityInputSerializer,
        responses={201: ResponseActivityCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, assignment_id):
        _assignment_for_request(request, assignment_id)
        serializer = ResponseActivityInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = _call_assigned_command(
            record_response_activity,
            assignment_id=assignment_id,
            actor=get_human_actor(request),
            command_id=values["command_id"],
            activity_kind=values["activity_kind"],
            details=values.get("details"),
        )
        return Response(
            {"data": ResponseActivitySerializer(result.value).data, "replayed": result.replayed},
            status=status.HTTP_200_OK if result.replayed else status.HTTP_201_CREATED,
        )


class AssignmentUnableView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_unable_to_respond",
        request=AssignmentUnableSerializer,
        responses={200: AssignmentCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, assignment_id):
        _assignment_for_request(request, assignment_id)
        serializer = AssignmentUnableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = _call_assigned_command(
            mark_unable_to_respond,
            assignment_id=assignment_id,
            actor=get_human_actor(request),
            command_id=values["command_id"],
            reason=values["reason"],
        )
        return _assignment_command_response(result)


class AssignmentCompleteView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="assignments_complete",
        request=AssignmentCompleteSerializer,
        responses={200: AssignmentCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, assignment_id):
        _assignment_for_request(request, assignment_id)
        serializer = AssignmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = _call_assigned_command(
            complete_assignment,
            assignment_id=assignment_id,
            actor=get_human_actor(request),
            command_id=values["command_id"],
            details=values["details"],
        )
        return _assignment_command_response(result)


class EvidenceUploadSessionView(APIView):
    permission_classes = (IsAuthenticatedHuman,)

    @extend_schema(
        operation_id="evidence_upload_sessions_create",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
        description="Upload sessions remain disabled because no storage provider is configured.",
    )
    def post(self, request):
        del request
        raise EvidenceStorageUnavailable()


class EvidenceUploadCompleteView(EvidenceUploadSessionView):
    @extend_schema(
        operation_id="evidence_upload_sessions_complete",
        request=None,
        responses={503: ErrorEnvelopeSerializer},
    )
    def post(self, request, session_id):
        del request, session_id
        raise EvidenceStorageUnavailable()


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSummarySerializer
    permission_classes = (IsAuthenticatedHuman,)

    def get_queryset(self):
        params = NotificationStatusQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        queryset = visible_notifications_queryset(get_human_actor(self.request).user)
        if status_filter := params.validated_data.get("status"):
            queryset = queryset.filter(status=status_filter)
        return queryset


class NotificationReadView(APIView):
    permission_classes = (IsAuthenticatedHuman,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensitive"

    @extend_schema(
        operation_id="notifications_mark_read",
        request=CommandIDSerializer,
        responses={200: NotificationCommandResponseSerializer, **API_ERROR_RESPONSES},
    )
    def post(self, request, notification_id):
        user = get_human_actor(request).user
        notification = visible_notifications_queryset(user).filter(pk=notification_id).first()
        if notification is None:
            raise NotFound
        serializer = CommandIDSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = mark_notification_read(
                notification_id=notification.pk,
                actor=HumanActor(user),
                command_id=serializer.validated_data["command_id"],
            )
        except AuthorizationDenied as exc:
            raise NotFound from exc
        return Response(
            {"data": NotificationSummarySerializer(result.value).data, "replayed": result.replayed}
        )
