"""Explicit request and response shapes for the public API."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.incidents.models import (
    AccidentCandidate,
    CandidateReviewerAssignment,
    IncidentStatus,
)
from apps.notifications.models import NotificationStatus
from apps.organizations.models import OrganizationMembership
from apps.responses.models import Response, ResponseActivityKind, ResponseAssignment

from .selectors import active_memberships_for


class ErrorEnvelopeSerializer(serializers.Serializer):
    code = serializers.CharField()
    detail = serializers.CharField()
    errors = serializers.JSONField(required=False)
    request_id = serializers.UUIDField(required=False)


class TokenPairResponseSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class AccessTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class SafeMembershipSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    organization_code = serializers.CharField(source="organization.code", read_only=True)
    organization_name = serializers.CharField(source="organization.display_name", read_only=True)
    organization_kind = serializers.CharField(
        source="organization.organization_kind", read_only=True
    )
    role = serializers.CharField(source="role_group.name", read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = (
            "id",
            "organization_id",
            "organization_code",
            "organization_name",
            "organization_kind",
            "role",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AuthenticatedUserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "roles", "memberships")
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, user):
        approved_names = {"ADMIN", "POLICE", "HOSPITAL"}
        return sorted(user.groups.filter(name__in=approved_names).values_list("name", flat=True))

    @extend_schema_field(SafeMembershipSerializer(many=True))
    def get_memberships(self, user):
        memberships = active_memberships_for(user)
        return SafeMembershipSerializer(memberships, many=True).data


class AccountProfileSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        disallowed = set(self.initial_data) - {"first_name", "last_name"}
        if disallowed:
            raise serializers.ValidationError(
                {
                    name: "This field cannot be changed through the profile endpoint."
                    for name in disallowed
                }
            )
        return attrs

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")
        read_only_fields = ("id", "email")


class IncidentSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    status = serializers.ChoiceField(choices=IncidentStatus.choices, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CandidateSummarySerializer(serializers.ModelSerializer):
    police_organization_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = AccidentCandidate
        fields = ("id", "police_organization_id", "status", "created_at", "updated_at")
        read_only_fields = fields


class CandidateReviewerAssignmentSerializer(serializers.ModelSerializer):
    candidate_id = serializers.UUIDField(read_only=True)
    police_organization_id = serializers.UUIDField(read_only=True)
    reviewer_id = serializers.UUIDField(read_only=True)
    assigned_by_user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = CandidateReviewerAssignment
        fields = (
            "id",
            "candidate_id",
            "police_organization_id",
            "reviewer_id",
            "assigned_by_user_id",
            "command_id",
            "assigned_at",
        )
        read_only_fields = fields


class AssignmentSummarySerializer(serializers.ModelSerializer):
    incident_id = serializers.UUIDField(read_only=True)
    target_organization_id = serializers.UUIDField(read_only=True)
    target_organization_kind = serializers.CharField(
        source="target_organization.organization_kind", read_only=True
    )

    class Meta:
        model = ResponseAssignment
        fields = (
            "id",
            "incident_id",
            "target_organization_id",
            "target_organization_kind",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ResponseActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Response
        fields = ("id", "activity_kind", "details", "occurred_at")
        read_only_fields = fields


class NotificationSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    status = serializers.ChoiceField(choices=NotificationStatus.choices, read_only=True)
    safe_message_code = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    read_at = serializers.DateTimeField(read_only=True, allow_null=True)


class AssignmentCommandResponseSerializer(serializers.Serializer):
    data = AssignmentSummarySerializer()
    replayed = serializers.BooleanField()


class CandidateReviewerAssignmentCommandResponseSerializer(serializers.Serializer):
    data = CandidateReviewerAssignmentSerializer()
    replayed = serializers.BooleanField()


class ResponseActivityCommandResponseSerializer(serializers.Serializer):
    data = ResponseActivitySerializer()
    replayed = serializers.BooleanField()


class NotificationCommandResponseSerializer(serializers.Serializer):
    data = NotificationSummarySerializer()
    replayed = serializers.BooleanField()


class DetectionEventCreatedSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    received_at = serializers.DateTimeField()


class CommandIDSerializer(serializers.Serializer):
    command_id = serializers.UUIDField()


class CandidateReviewerAssignmentInputSerializer(CommandIDSerializer):
    reviewer_id = serializers.UUIDField()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=False)


class AssignmentStartSerializer(CommandIDSerializer):
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class AssignmentCompleteSerializer(CommandIDSerializer):
    details = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class AssignmentUnableSerializer(CommandIDSerializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class ResponseActivityInputSerializer(CommandIDSerializer):
    activity_kind = serializers.ChoiceField(choices=ResponseActivityKind.choices)
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)


class NotificationStatusQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=NotificationStatus.choices, required=False)


class IncidentStatusQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=IncidentStatus.choices, required=False)


class DetectionEventInputSerializer(serializers.Serializer):
    video_source_id = serializers.UUIDField()
    external_event_id = serializers.CharField(max_length=128, trim_whitespace=True)
    model_name = serializers.CharField(max_length=100, trim_whitespace=True)
    model_version = serializers.CharField(max_length=100, trim_whitespace=True)
    detected_at = serializers.DateTimeField()
    processing_outcome = serializers.ChoiceField(choices=("OBSERVATION", "UNCERTAIN"))
    confidence = serializers.DecimalField(
        max_digits=5, decimal_places=4, min_value=0, max_value=1, required=False, allow_null=True
    )
    payload_sha256 = serializers.RegexField(r"^[0-9a-fA-F]{64}$", required=False, allow_null=True)
    metadata_schema_version = serializers.IntegerField(min_value=1, default=1)
    auxiliary_metadata = serializers.DictField(required=False, default=dict)
