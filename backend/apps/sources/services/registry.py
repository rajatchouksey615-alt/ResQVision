"""Policy-gated management of authorized video sources."""

from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_denied_action, record_successful_action
from apps.organizations.models import Organization
from apps.sources.models import (
    VideoSource,
)
from apps.sources.models import (
    VideoSourceAuthorizationStatus as AuthStatus,
)
from apps.sources.models import (
    VideoSourceAvailabilityStatus as AvailabilityStatus,
)
from common.domain.actors import Actor
from common.domain.authorization import require_human
from common.domain.exceptions import (
    AuthorizationDenied,
    InvalidStateTransition,
    PolicyNotConfigured,
    ResourceConflict,
    ResourceNotFound,
)
from common.domain.policies import AuthorizationPolicy, require_authorized


def _audit_denied(actor: Actor, source_id: UUID | None, operation: str) -> None:
    record_denied_action(
        actor=actor,
        action="DOMAIN_ACTION_DENIED",
        resource_type="VIDEO_SOURCE",
        resource_id=source_id,
        safe_context={"reason_code": operation},
    )


def register_video_source(
    *,
    actor: Actor,
    source_code: str,
    name: str,
    source_type: str,
    processing_policy_ref: str,
    retention_policy_ref: str,
    owner_organization_id: UUID | None = None,
    owner_external_ref: str | None = None,
    policy: AuthorizationPolicy | None = None,
) -> VideoSource:
    try:
        require_human(actor)
        owner = None
        if owner_organization_id is not None:
            owner = Organization.objects.filter(pk=owner_organization_id).first()
            if owner is None:
                raise ResourceNotFound("Source owner organization was not found.")
            if not owner.is_active:
                raise AuthorizationDenied(
                    "An inactive organization cannot own an authorized source."
                )
        source = VideoSource(
            source_code=source_code,
            name=name,
            source_type=source_type,
            owner_organization=owner,
            owner_external_ref=owner_external_ref,
            processing_policy_ref=processing_policy_ref,
            retention_policy_ref=retention_policy_ref,
        )
        require_authorized(policy, "source.register", actor, source)
        source.full_clean()
        source.save()
        record_successful_action(
            actor=actor,
            action="VIDEO_SOURCE_REGISTERED",
            resource_type="VIDEO_SOURCE",
            resource_id=source.pk,
        )
        return source
    except AuthorizationDenied, PolicyNotConfigured:
        _audit_denied(actor, None, "source.register")
        raise
    except IntegrityError as exc:
        raise ResourceConflict("A video source with this code already exists.") from exc


def validate_source_for_ingestion(source: VideoSource | UUID) -> VideoSource:
    """Return an authorized source; caller may lock it before validating."""

    if not isinstance(source, VideoSource):
        try:
            source = VideoSource.objects.get(pk=source)
        except VideoSource.DoesNotExist as exc:
            raise ResourceNotFound("Video source was not found.") from exc
    if (
        source.authorization_status != AuthStatus.AUTHORIZED
        or source.availability_status == AvailabilityStatus.UNAVAILABLE
    ):
        raise AuthorizationDenied("The video source is not authorized for ingestion.")
    return source


def _transition_source(
    *,
    source_id: UUID,
    actor: Actor,
    operation: str,
    target: str,
    policy: AuthorizationPolicy | None,
    authorization_reference: str | None = None,
) -> VideoSource:
    try:
        user = require_human(actor)
        with transaction.atomic():
            source = VideoSource.objects.select_for_update().filter(pk=source_id).first()
            if source is None:
                raise ResourceNotFound("Video source was not found.")
            require_authorized(policy, operation, actor, source)
            if target == AuthStatus.AUTHORIZED:
                if not authorization_reference or not authorization_reference.strip():
                    raise InvalidStateTransition("An authorization reference is required.")
                if source.authorization_status not in {
                    AuthStatus.PENDING_REVIEW,
                    AuthStatus.SUSPENDED,
                }:
                    raise InvalidStateTransition("The source cannot be authorized from this state.")
                source.authorization_status = target
                source.authorized_by_user = user
                source.authorized_at = timezone.now()
                source.authorization_reference = authorization_reference.strip()
            else:
                if source.authorization_status in {AuthStatus.REVOKED, target}:
                    raise InvalidStateTransition("The source cannot enter the requested state.")
                source.authorization_status = target
                source.authorized_by_user = None
                source.authorized_at = None
            source.full_clean()
            source.save(
                update_fields=[
                    "authorization_status",
                    "authorized_by_user",
                    "authorized_at",
                    "authorization_reference",
                    "updated_at",
                ]
            )
            action = {
                AuthStatus.AUTHORIZED: "VIDEO_SOURCE_AUTHORIZED",
                AuthStatus.SUSPENDED: "VIDEO_SOURCE_SUSPENDED",
                AuthStatus.REVOKED: "VIDEO_SOURCE_REVOKED",
            }[target]
            record_successful_action(
                actor=actor,
                action=action,
                resource_type="VIDEO_SOURCE",
                resource_id=source.pk,
                safe_context={"to_status": target},
            )
            return source
    except AuthorizationDenied, PolicyNotConfigured, InvalidStateTransition:
        _audit_denied(actor, source_id, operation)
        raise


def authorize_video_source(
    *, source_id: UUID, actor: Actor, authorization_reference: str, policy=None
) -> VideoSource:
    return _transition_source(
        source_id=source_id,
        actor=actor,
        operation="source.authorize",
        target=AuthStatus.AUTHORIZED,
        policy=policy,
        authorization_reference=authorization_reference,
    )


def suspend_video_source(*, source_id: UUID, actor: Actor, policy=None) -> VideoSource:
    return _transition_source(
        source_id=source_id,
        actor=actor,
        operation="source.suspend",
        target=AuthStatus.SUSPENDED,
        policy=policy,
    )


def revoke_video_source(*, source_id: UUID, actor: Actor, policy=None) -> VideoSource:
    return _transition_source(
        source_id=source_id,
        actor=actor,
        operation="source.revoke",
        target=AuthStatus.REVOKED,
        policy=policy,
    )
