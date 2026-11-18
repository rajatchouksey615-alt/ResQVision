import 'dart:convert';

import '../../../core/errors/app_exception.dart';
import '../../../core/networking/api_request.dart';
import '../../../core/networking/authenticated_api_client.dart';
import '../../authentication/data/models/authenticated_user.dart';

enum DashboardRole {
  admin,
  police,
  hospital;

  String get code => name.toUpperCase();

  String get title => switch (this) {
    DashboardRole.admin => 'Admin',
    DashboardRole.police => 'Police',
    DashboardRole.hospital => 'Hospital',
  };

  static DashboardRole? fromCode(String code) => switch (code) {
    'ADMIN' => DashboardRole.admin,
    'POLICE' => DashboardRole.police,
    'HOSPITAL' => DashboardRole.hospital,
    _ => null,
  };
}

class DashboardDataException implements Exception {
  const DashboardDataException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class DashboardAssignment {
  const DashboardAssignment({
    required this.id,
    required this.organizationId,
    required this.organizationKind,
    required this.organizationName,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String organizationId;
  final String organizationKind;
  final String organizationName;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
}

class DashboardIncident {
  const DashboardIncident({
    required this.id,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.assignments,
  });

  final String id;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<DashboardAssignment> assignments;
}

class DashboardPage {
  const DashboardPage({
    required this.incidents,
    required this.totalCount,
    required this.nextOffset,
    required this.hasMore,
    required this.isPartial,
  });

  final List<DashboardIncident> incidents;

  /// Count returned for the authenticated user's combined authorized scope.
  /// It is deliberately not presented as a role-specific or global metric.
  final int totalCount;
  final int nextOffset;
  final bool hasMore;
  final bool isPartial;
}

class _AssignmentLoadResult {
  const _AssignmentLoadResult({
    required this.assignments,
    this.isPartial = false,
  });

  final List<DashboardAssignment>? assignments;
  final bool isPartial;
}

class DashboardRepository {
  DashboardRepository({required AuthenticatedApiClient apiClient})
    : _apiClient = apiClient;

  final AuthenticatedApiClient _apiClient;
  static const int pageSize = 5;
  static const int assignmentPageSize = 100;

  Future<DashboardPage> loadPage({
    required DashboardRole role,
    required List<OrganizationMembership> activeMemberships,
    required String? organizationId,
    int offset = 0,
  }) async {
    if (offset < 0) throw ArgumentError.value(offset, 'offset');
    final List<OrganizationMembership> eligibleMemberships =
        _eligibleMemberships(role, activeMemberships);
    if (role != DashboardRole.admin && eligibleMemberships.isEmpty) {
      throw DashboardDataException(
        'No active ${role.title.toLowerCase()} organization membership is available for this workspace.',
      );
    }
    if (organizationId != null &&
        !eligibleMemberships.any(
          (OrganizationMembership item) =>
              item.organizationId == organizationId,
        )) {
      throw const DashboardDataException(
        'The selected organization is not an active membership on this account.',
      );
    }

    final ApiResponse response = await _request(
      'incidents/?limit=$pageSize&offset=$offset',
      requestName: 'incident list',
    );
    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'incident page',
    );
    final int totalCount = _requiredInt(payload, 'count', 'incident page');
    final Object? rows = payload['results'];
    if (rows is! List<Object?>) {
      throw const DashboardDataException(
        'The incident response did not match the expected format.',
      );
    }
    final String? next = _nullableString(payload, 'next', 'incident page');
    final int nextOffset = next == null
        ? offset
        : _offsetFromNext(next, offset);
    bool partial = false;

    final Map<String, OrganizationMembership> membershipsById =
        <String, OrganizationMembership>{
          for (final OrganizationMembership item in eligibleMemberships)
            item.organizationId: item,
        };
    final List<DashboardIncident> incidents = <DashboardIncident>[];
    for (final Object? row in rows) {
      final Map<String, Object?> incident = _asObject(row, 'incident');
      final String incidentId = _requiredUuid(incident, 'id', 'incident');
      final _AssignmentLoadResult assignmentResult = await _loadAssignments(
        incidentId: incidentId,
        role: role,
        eligibleMemberships: membershipsById,
        organizationId: organizationId,
      );
      partial = partial || assignmentResult.isPartial;
      final List<DashboardAssignment>? assignments =
          assignmentResult.assignments;
      if (assignments == null) {
        partial = true;
        continue;
      }
      if (assignments.isEmpty) continue;
      final String status = _requiredString(incident, 'status', 'incident');
      final DateTime createdAt = _requiredDate(
        incident,
        'created_at',
        'incident',
      );
      final DateTime updatedAt = _requiredDate(
        incident,
        'updated_at',
        'incident',
      );
      incidents.add(
        DashboardIncident(
          id: incidentId,
          status: status,
          createdAt: createdAt,
          updatedAt: updatedAt,
          assignments: List<DashboardAssignment>.unmodifiable(assignments),
        ),
      );
    }

    return DashboardPage(
      incidents: List<DashboardIncident>.unmodifiable(incidents),
      totalCount: totalCount,
      nextOffset: nextOffset,
      hasMore: next != null,
      isPartial: partial,
    );
  }

  Future<_AssignmentLoadResult> _loadAssignments({
    required String incidentId,
    required DashboardRole role,
    required Map<String, OrganizationMembership> eligibleMemberships,
    required String? organizationId,
  }) async {
    final ApiResponse response;
    try {
      response = await _apiClient.request(
        'GET',
        'incidents/$incidentId/assignments/?limit=$assignmentPageSize&offset=0',
      );
    } on AppException catch (error) {
      throw DashboardDataException(error.message);
    }
    // A visible incident can leave scope between the list and its assignment read.
    if (response.statusCode == 404) {
      return const _AssignmentLoadResult(assignments: null, isPartial: true);
    }
    _expectSuccess(response, 'assignment list');

    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'assignment page',
    );
    final Object? rows = payload['results'];
    if (rows is! List<Object?>) {
      throw const DashboardDataException(
        'The assignment response did not match the expected format.',
      );
    }
    final String? next = _nullableString(payload, 'next', 'assignment page');
    final List<DashboardAssignment> assignments = <DashboardAssignment>[];
    for (final Object? row in rows) {
      final Map<String, Object?> assignment = _asObject(row, 'assignment');
      final String assignedIncidentId = _requiredUuid(
        assignment,
        'incident_id',
        'assignment',
      );
      if (assignedIncidentId != incidentId) {
        throw const DashboardDataException(
          'The assignment response did not match the requested incident.',
        );
      }
      final String targetId = _requiredUuid(
        assignment,
        'target_organization_id',
        'assignment',
      );
      final String kind = _requiredString(
        assignment,
        'target_organization_kind',
        'assignment',
      );
      final OrganizationMembership? membership = eligibleMemberships[targetId];
      if (membership == null ||
          (organizationId != null && targetId != organizationId) ||
          membership.organizationKind != kind ||
          (role != DashboardRole.admin && kind != role.code)) {
        continue;
      }
      assignments.add(
        DashboardAssignment(
          id: _requiredUuid(assignment, 'id', 'assignment'),
          organizationId: targetId,
          organizationKind: kind,
          organizationName: membership.organizationName,
          status: _requiredString(assignment, 'status', 'assignment'),
          createdAt: _requiredDate(assignment, 'created_at', 'assignment'),
          updatedAt: _requiredDate(assignment, 'updated_at', 'assignment'),
        ),
      );
    }
    return _AssignmentLoadResult(
      assignments: assignments,
      isPartial: next != null,
    );
  }

  Future<ApiResponse> _request(
    String path, {
    required String requestName,
  }) async {
    try {
      final ApiResponse response = await _apiClient.request('GET', path);
      _expectSuccess(response, requestName);
      return response;
    } on AppException catch (error) {
      throw DashboardDataException(error.message);
    }
  }

  void _expectSuccess(ApiResponse response, String requestName) {
    if (response.statusCode == 200) return;
    final int status = response.statusCode;
    final String message = switch (status) {
      401 => 'Your session is no longer authorized. Sign in again.',
      403 => 'You do not have access to this operational data.',
      404 => 'The requested operational data is no longer available.',
      429 => 'Dashboard data is rate limited. Try again shortly.',
      >= 500 => 'Dashboard data is temporarily unavailable. Try again.',
      _ => 'The $requestName could not be loaded.',
    };
    throw DashboardDataException(message, statusCode: status);
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

  Map<String, Object?> _decodeObject(String body, String resource) {
    try {
      return _asObject(jsonDecode(body), resource);
    } on FormatException {
      throw DashboardDataException(
        'The $resource response did not match the expected format.',
      );
    }
  }

  Map<String, Object?> _asObject(Object? value, String resource) {
    if (value is Map<String, dynamic>) return value;
    throw DashboardDataException(
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
    throw DashboardDataException(
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
    throw DashboardDataException(
      'The $resource response did not match the expected format.',
    );
  }

  int _requiredInt(Map<String, Object?> value, String key, String resource) {
    final Object? field = value[key];
    if (field is int && field >= 0) return field;
    throw DashboardDataException(
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
    throw DashboardDataException(
      'The $resource response did not match the expected format.',
    );
  }

  DateTime _requiredDate(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final String raw = _requiredString(value, key, resource);
    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed != null) return parsed;
    throw DashboardDataException(
      'The $resource response did not match the expected format.',
    );
  }

  int _offsetFromNext(String next, int currentOffset) {
    final Uri? uri = Uri.tryParse(next);
    final String? rawOffset = uri?.queryParameters['offset'];
    final int? nextOffset = int.tryParse(rawOffset ?? '');
    if (nextOffset == null || nextOffset <= currentOffset) {
      throw const DashboardDataException(
        'The incident page did not contain a valid next offset.',
      );
    }
    return nextOffset;
  }
}
