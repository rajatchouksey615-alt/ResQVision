"""Central v1 route table; no domain app owns a duplicate URL prefix."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from .views import (
    AccountProfileView,
    AssignmentAcknowledgeView,
    AssignmentActivityView,
    AssignmentCompleteView,
    AssignmentDetailView,
    AssignmentStartView,
    AssignmentUnableView,
    AuthenticatedUserView,
    BlockedAssignmentCancelView,
    BlockedAssignmentReassignView,
    BlockedIncidentCloseView,
    BlockedIncidentResolveView,
    BlockedSourceCollectionView,
    BlockedSourceDetailView,
    CandidateAssociateEventsView,
    CandidateCollectionView,
    CandidateDetailView,
    CandidateReviewerAssignmentCreateView,
    CandidateReviewView,
    DetectionEventSubmissionView,
    EmailTokenView,
    EvidenceCollectionView,
    EvidenceDetailView,
    EvidenceUploadCompleteView,
    EvidenceUploadSessionView,
    IncidentAssignmentsView,
    IncidentDetailView,
    IncidentListView,
    IncidentLocationView,
    LogoutView,
    MyMembershipsView,
    NotificationListView,
    NotificationReadView,
    OrganizationMembershipSummaryView,
    PasswordChangeView,
    RefreshTokenView,
)

app_name = "api_v1"


class PublicSchemaView(SpectacularAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)


class PublicDocsView(SpectacularSwaggerView):
    authentication_classes = ()
    permission_classes = (AllowAny,)


urlpatterns = [
    path("schema/", PublicSchemaView.as_view(), name="schema"),
    path("docs/", PublicDocsView.as_view(url_name="api_v1:schema"), name="docs"),
    path("auth/token/", EmailTokenView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", AuthenticatedUserView.as_view(), name="auth_me"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password_change"),
    path("accounts/me/", AccountProfileView.as_view(), name="account_me"),
    path("organizations/me/", MyMembershipsView.as_view(), name="my_memberships"),
    path(
        "organizations/<uuid:organization_id>/memberships/",
        OrganizationMembershipSummaryView.as_view(),
        name="organization_my_membership",
    ),
    path(
        "video-sources/", BlockedSourceCollectionView.as_view(), name="video_source_list_register"
    ),
    path(
        "video-sources/<uuid:source_id>/",
        BlockedSourceDetailView.as_view(),
        name="video_source_detail",
    ),
    path(
        "ai/detection-events/",
        DetectionEventSubmissionView.as_view(),
        name="detection_event_submit",
    ),
    path("candidates/", CandidateCollectionView.as_view(), name="candidate_list"),
    path("candidates/<uuid:candidate_id>/", CandidateDetailView.as_view(), name="candidate_detail"),
    path(
        "candidates/<uuid:candidate_id>/assignment/",
        CandidateReviewerAssignmentCreateView.as_view(),
        name="candidate_reviewer_assignment_create",
    ),
    path(
        "candidates/<uuid:candidate_id>/associate-events/",
        CandidateAssociateEventsView.as_view(),
        name="candidate_associate_events",
    ),
    path(
        "candidates/<uuid:candidate_id>/review/",
        CandidateReviewView.as_view(),
        name="candidate_review",
    ),
    path("incidents/", IncidentListView.as_view(), name="incident_list"),
    path("incidents/<uuid:incident_id>/", IncidentDetailView.as_view(), name="incident_detail"),
    path(
        "incidents/<uuid:incident_id>/resolve/",
        BlockedIncidentResolveView.as_view(),
        name="incident_resolve",
    ),
    path(
        "incidents/<uuid:incident_id>/close/",
        BlockedIncidentCloseView.as_view(),
        name="incident_close",
    ),
    path(
        "incidents/<uuid:incident_id>/assignments/",
        IncidentAssignmentsView.as_view(),
        name="incident_assignments",
    ),
    path(
        "assignments/<uuid:assignment_id>/",
        AssignmentDetailView.as_view(),
        name="assignment_detail",
    ),
    path(
        "assignments/<uuid:assignment_id>/acknowledge/",
        AssignmentAcknowledgeView.as_view(),
        name="assignment_acknowledge",
    ),
    path(
        "assignments/<uuid:assignment_id>/start/",
        AssignmentStartView.as_view(),
        name="assignment_start",
    ),
    path(
        "assignments/<uuid:assignment_id>/activities/",
        AssignmentActivityView.as_view(),
        name="assignment_activity",
    ),
    path(
        "assignments/<uuid:assignment_id>/unable-to-respond/",
        AssignmentUnableView.as_view(),
        name="assignment_unable_to_respond",
    ),
    path(
        "assignments/<uuid:assignment_id>/complete/",
        AssignmentCompleteView.as_view(),
        name="assignment_complete",
    ),
    path(
        "assignments/<uuid:assignment_id>/cancel/",
        BlockedAssignmentCancelView.as_view(),
        name="assignment_cancel",
    ),
    path(
        "assignments/<uuid:assignment_id>/reassign/",
        BlockedAssignmentReassignView.as_view(),
        name="assignment_reassign",
    ),
    path("evidence/", EvidenceCollectionView.as_view(), name="evidence_list"),
    path("evidence/<uuid:evidence_id>/", EvidenceDetailView.as_view(), name="evidence_detail"),
    path(
        "evidence/upload-sessions/",
        EvidenceUploadSessionView.as_view(),
        name="evidence_upload_session",
    ),
    path(
        "evidence/upload-sessions/<uuid:session_id>/complete/",
        EvidenceUploadCompleteView.as_view(),
        name="evidence_upload_complete",
    ),
    path(
        "incidents/<uuid:incident_id>/locations/",
        IncidentLocationView.as_view(),
        name="incident_locations",
    ),
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/<uuid:notification_id>/read/",
        NotificationReadView.as_view(),
        name="notification_read",
    ),
]
