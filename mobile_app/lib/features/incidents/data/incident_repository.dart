import 'dart:convert';

import '../../../core/errors/app_exception.dart';
import '../../../core/networking/api_request.dart';
import '../../../core/networking/authenticated_api_client.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../../dashboard/data/dashboard_repository.dart';

class IncidentDataException implements Exception {
  const IncidentDataException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ManagedIncident {
  const ManagedIncident({
    required this.id,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    this.assignments = const <IncidentAssignment>[],
    this.assignmentsArePartial = false,
  });

  final String id;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<IncidentAssignment> assignments;
  final bool assignmentsArePartial;

  ManagedIncident withAssignments(
    List<IncidentAssignment> value, {
    required bool isPartial,
  }) => ManagedIncident(
    id: id,
    status: status,
    createdAt: createdAt,
    updatedAt: updatedAt,
    assignments: List<IncidentAssignment>.unmodifiable(value),
    assignmentsArePartial: isPartial,
  );
}

class IncidentAssignment {
  const IncidentAssignment({
    required this.id,
    required this.incidentId,
    required this.organizationId,
    required this.organizationKind,
    required this.organizationName,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String incidentId;
  final String organizationId;
  final String organizationKind;
  final String organizationName;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
}

class ManagedIncidentPage {
  const ManagedIncidentPage({
    required this.incidents,
    required this.totalCount,
    required this.nextOffset,
    required this.hasMore,
    required this.isPartial,
  });

  final List<ManagedIncident> incidents;
  final int totalCount;
  final int nextOffset;
  final bool hasMore;
  final bool isPartial;
}

class ManagedIncidentDetail {
  const ManagedIncidentDetail({
    required this.incident,
    required this.assignments,
    required this.assignmentsArePartial,
  });

  final ManagedIncident incident;
  final List<IncidentAssignment> assignments;
  final bool assignmentsArePartial;
}

class _AssignmentLoadResult {
  const _AssignmentLoadResult({
    required this.assignments,
    this.isPartial = false,
  });

  final List<IncidentAssignment>? assignments;
  final bool isPartial;
}

/// Reads backend-authorized incidents without adding client-side lifecycle rules.
class IncidentRepository {
  IncidentRepository({required AuthenticatedApiClient apiClient})
    : _apiClient = apiClient;

  final AuthenticatedApiClient _apiClient;

  static const int pageSize = 10;
  static const int assignmentPageSize = 100;
  static const List<String> supportedStatuses = <String>[
    'OPEN',
    'RESPONSE_ACTIVE',
    'RESOLVED',
    'CLOSED',
  ];

  Future<ManagedIncidentPage> loadPage({
    required DashboardRole role,
    required List<OrganizationMembership> activeMemberships,
    String? organizationId,
    String? status,
    int offset = 0,
  }) async {
    if (offset < 0) throw ArgumentError.value(offset, 'offset');
    if (status != null && !supportedStatuses.contains(status)) {
      throw ArgumentError.value(status, 'status');
    }
    _validateScope(role, activeMemberships, organizationId);

    final Map<String, String> query = <String, String>{
      'limit': '$pageSize',
      'offset': '$offset',
      'status': ?status,
    };
    final ApiResponse response = await _request(
      'GET',
      'incidents/?${Uri(queryParameters: query).query}',
      requestName: 'incident list',
    );
    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'incident page',
    );
    final int totalCount = _requiredInt(payload, 'count', 'incident page');
    final Object? rawRows = payload['results'];
    if (rawRows is! List<Object?>) {
      throw const IncidentDataException(
        'The incident response did not match the expected format.',
      );
    }
    final String? next = _nullableString(payload, 'next', 'incident page');
    final int nextOffset = next == null
        ? offset
        : _offsetFromNext(next, offset);
    final List<OrganizationMembership> memberships = _eligibleMemberships(
      role,
      activeMemberships,
    );
    final Map<String, OrganizationMembership> membershipsById =
        <String, OrganizationMembership>{
          for (final OrganizationMembership membership in memberships)
            membership.organizationId: membership,
        };
    final List<ManagedIncident> incidents = <ManagedIncident>[];
    bool isPartial = false;
    for (final Object? row in rawRows) {
      final ManagedIncident incident = _parseIncident(row);
      final _AssignmentLoadResult assignmentResult = await _loadAssignments(
        incidentId: incident.id,
        eligibleMemberships: membershipsById,
        organizationId: organizationId,
      );
      isPartial = isPartial || assignmentResult.isPartial;
      final List<IncidentAssignment>? assignments =
          assignmentResult.assignments;
      if (assignments == null) {
        isPartial = true;
        continue;
      }
      if (assignments.isEmpty) continue;
      incidents.add(
        incident.withAssignments(
          assignments,
          isPartial: assignmentResult.isPartial,
        ),
      );
    }

    return ManagedIncidentPage(
      incidents: List<ManagedIncident>.unmodifiable(incidents),
      totalCount: totalCount,
      nextOffset: nextOffset,
      hasMore: next != null,
      isPartial: isPartial,
    );
  }

  Future<ManagedIncidentDetail> loadDetail({
    required String incidentId,
    required DashboardRole role,
    required List<OrganizationMembership> activeMemberships,
    String? organizationId,
  }) async {
    _validateScope(role, activeMemberships, organizationId);
    final ApiResponse detailResponse = await _request(
      'GET',
      'incidents/$incidentId/',
      requestName: 'incident detail',
    );
    final ManagedIncident incident = _parseIncident(
      _decodeObject(detailResponse.body, 'incident'),
    );
    if (incident.id != incidentId) {
      throw const IncidentDataException(
        'The incident response did not match the requested record.',
      );
    }

    final List<OrganizationMembership> memberships = _eligibleMemberships(
      role,
      activeMemberships,
    );
    final Map<String, OrganizationMembership> byId =
        <String, OrganizationMembership>{
          for (final OrganizationMembership membership in memberships)
            membership.organizationId: membership,
        };
    final _AssignmentLoadResult assignmentResult = await _loadAssignments(
      incidentId: incidentId,
      eligibleMemberships: byId,
      organizationId: organizationId,
    );
    if (assignmentResult.assignments == null) {
      throw const IncidentDataException(
        'This incident is unavailable in your authorized scope.',
        statusCode: 404,
      );
    }
    return ManagedIncidentDetail(
      incident: incident,
      assignments: assignmentResult.assignments!,
      assignmentsArePartial: assignmentResult.isPartial,
    );
  }

  Future<_AssignmentLoadResult> _loadAssignments({
    required String incidentId,
    required Map<String, OrganizationMembership> eligibleMemberships,
    required String? organizationId,
  }) async {
    final ApiResponse response;
    try {
      response = await _request(
        'GET',
        'incidents/$incidentId/assignments/?limit=$assignmentPageSize&offset=0',
        requestName: 'assignment list',
      );
    } on IncidentDataException catch (error) {
      if (error.statusCode == 404) {
        return const _AssignmentLoadResult(assignments: null, isPartial: true);
      }
      rethrow;
    }
    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'assignment page',
    );
    final Object? rows = payload['results'];
    if (rows is! List<Object?>) {
      throw const IncidentDataException(
        'The assignment response did not match the expected format.',
      );
    }
    final List<IncidentAssignment> assignments = <IncidentAssignment>[];
    for (final Object? row in rows) {
      final Map<String, Object?> raw = _asObject(row, 'assignment');
      final String assignedIncidentId = _requiredUuid(
        raw,
        'incident_id',
        'assignment',
      );
      if (assignedIncidentId != incidentId) {
        throw const IncidentDataException(
          'The assignment response did not match the requested incident.',
        );
      }
      final String targetOrganizationId = _requiredUuid(
        raw,
        'target_organization_id',
        'assignment',
      );
      final String organizationKind = _requiredString(
        raw,
        'target_organization_kind',
        'assignment',
      );
      final OrganizationMembership? membership =
          eligibleMemberships[targetOrganizationId];
      if (membership == null ||
          membership.organizationKind != organizationKind ||
          (organizationId != null && targetOrganizationId != organizationId)) {
        continue;
      }
      assignments.add(
        IncidentAssignment(
          id: _requiredUuid(raw, 'id', 'assignment'),
          incidentId: assignedIncidentId,
          organizationId: targetOrganizationId,
          organizationKind: organizationKind,
          organizationName: membership.organizationName,
          status: _requiredString(raw, 'status', 'assignment'),
          createdAt: _requiredDate(raw, 'created_at', 'assignment'),
          updatedAt: _requiredDate(raw, 'updated_at', 'assignment'),
        ),
      );
    }
    return _AssignmentLoadResult(
      assignments: List<IncidentAssignment>.unmodifiable(assignments),
      isPartial: _nullableString(payload, 'next', 'assignment page') != null,
    );
  }

  void _validateScope(
    DashboardRole role,
    List<OrganizationMembership> memberships,
    String? organizationId,
  ) {
    final List<OrganizationMembership> eligible = _eligibleMemberships(
      role,
      memberships,
    );
    if (role != DashboardRole.admin && eligible.isEmpty) {
      throw IncidentDataException(
        'No active ${role.title.toLowerCase()} organization membership is available for this workspace.',
      );
    }
    if (organizationId != null &&
        !eligible.any(
          (OrganizationMembership item) =>
              item.organizationId == organizationId,
        )) {
      throw const IncidentDataException(
        'The selected organization is not an active membership on this account.',
      );
    }
  }

  List<OrganizationMembership> _eligibleMemberships(
    DashboardRole role,
    List<OrganizationMembership> memberships,
  ) => memberships
      .where((OrganizationMembership item) {
        if (item.status != 'ACTIVE') return false;
        if (role == DashboardRole.admin) {
          return item.role == item.organizationKind &&
              (item.organizationKind == 'POLICE' ||
                  item.organizationKind == 'HOSPITAL');
        }
        return item.role == role.code && item.organizationKind == role.code;
      })
      .toList(growable: false);

  Future<ApiResponse> _request(
    String method,
    String path, {
    required String requestName,
  }) async {
    try {
      final ApiResponse response = await _apiClient.request(method, path);
      if (response.statusCode != 200) {
        final int status = response.statusCode;
        throw IncidentDataException(switch (status) {
          401 => 'Your session is no longer authorized. Sign in again.',
          403 => 'You do not have access to this incident data.',
          404 => 'This incident is unavailable in your authorized scope.',
          409 =>
            'This incident changed while it was loading. Refresh and try again.',
          429 => 'Incident data is rate limited. Try again shortly.',
          503 =>
            'This operation is unavailable while its backend policy is pending approval.',
          >= 500 => 'Incident data is temporarily unavailable. Try again.',
          _ => 'The $requestName could not be loaded.',
        }, statusCode: status);
      }
      return response;
    } on AppException catch (error) {
      throw IncidentDataException(error.message);
    }
  }

  ManagedIncident _parseIncident(Object? value) {
    final Map<String, Object?> raw = _asObject(value, 'incident');
    final String status = _requiredString(raw, 'status', 'incident');
    if (!supportedStatuses.contains(status)) {
      throw const IncidentDataException(
        'The incident response contained an unsupported status.',
      );
    }
    return ManagedIncident(
      id: _requiredUuid(raw, 'id', 'incident'),
      status: status,
      createdAt: _requiredDate(raw, 'created_at', 'incident'),
      updatedAt: _requiredDate(raw, 'updated_at', 'incident'),
    );
  }

  Map<String, Object?> _decodeObject(String body, String resource) {
    try {
      return _asObject(jsonDecode(body), resource);
    } on FormatException {
      throw IncidentDataException(
        'The $resource response did not match the expected format.',
      );
    }
  }

  Map<String, Object?> _asObject(Object? value, String resource) {
    if (value is Map<String, dynamic>) return value;
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  String _requiredString(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final Object? field = value[key];
    if (field is String && field.isNotEmpty) return field;
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  String _requiredUuid(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final String field = _requiredString(value, key, resource);
    if (RegExp(
      r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
    ).hasMatch(field)) {
      return field;
    }
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  int _requiredInt(Map<String, Object?> value, String key, String resource) {
    final Object? field = value[key];
    if (field is int && field >= 0) return field;
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  String? _nullableString(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final Object? field = value[key];
    if (field == null || field is String) return field as String?;
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  DateTime _requiredDate(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final DateTime? parsed = DateTime.tryParse(
      _requiredString(value, key, resource),
    );
    if (parsed != null) return parsed;
    throw IncidentDataException(
      'The $resource response did not match the expected format.',
    );
  }

  int _offsetFromNext(String next, int currentOffset) {
    final Uri? uri = Uri.tryParse(next);
    final int? nextOffset = int.tryParse(uri?.queryParameters['offset'] ?? '');
    if (nextOffset == null || nextOffset <= currentOffset) {
      throw const IncidentDataException(
        'The incident page did not contain a valid next offset.',
      );
    }
    return nextOffset;
  }
}
