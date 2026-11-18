import 'dart:convert';

import 'package:resqvision_mobile/core/networking/api_request.dart';

const String policeOrganizationId = '6b0eb8c2-9f06-4cac-83ed-56b7654b9f4c';
const String secondPoliceOrganizationId =
    '1419757d-5bf5-4f5a-9c11-2e9e1a462607';
const String hospitalOrganizationId = 'd82288ab-d351-4a2f-a440-88007b654b3d';
const String firstIncidentId = '732dfcb2-01ec-427c-9505-548bcc3fb020';
const String secondIncidentId = 'ecc70b40-93a2-482c-8832-8d97ad89fd5b';
const String policeAssignmentId = '77e1c81c-1b8f-4bea-9189-b697342a6f4e';
const String hospitalAssignmentId = '626c6796-98d5-4cc7-8fc6-119a1aa5ec5a';

Map<String, Object?> dashboardProfile({
  List<String> roles = const <String>['POLICE'],
  List<Map<String, Object?>>? memberships,
}) => <String, Object?>{
  'id': 'fbdc2770-2bcd-427b-9856-ef8e73d46752',
  'email': 'reviewer@example.test',
  'first_name': 'Rajat',
  'last_name': 'Reviewer',
  'roles': roles,
  'memberships': memberships ?? <Map<String, Object?>>[policeMembership()],
};

Map<String, Object?> policeMembership({
  String id = policeOrganizationId,
  String name = 'Central Police',
  String code = 'central-police',
  String status = 'ACTIVE',
}) =>
    membership(id: id, name: name, code: code, role: 'POLICE', status: status);

Map<String, Object?> hospitalMembership({
  String id = hospitalOrganizationId,
  String name = 'Central Hospital',
  String code = 'central-hospital',
  String status = 'ACTIVE',
}) => membership(
  id: id,
  name: name,
  code: code,
  role: 'HOSPITAL',
  status: status,
);

Map<String, Object?> membership({
  required String id,
  required String name,
  required String code,
  required String role,
  String status = 'ACTIVE',
}) => <String, Object?>{
  'id': 'e751879f-4ab3-42f3-9d6d-8e867503b00d',
  'organization_id': id,
  'organization_code': code,
  'organization_name': name,
  'organization_kind': role,
  'role': role,
  'status': status,
  'created_at': '2026-11-17T10:00:00Z',
};

Map<String, Object?> incident({
  String id = firstIncidentId,
  String status = 'OPEN',
  String createdAt = '2026-11-17T09:30:00Z',
}) => <String, Object?>{
  'id': id,
  'status': status,
  'created_at': createdAt,
  'updated_at': createdAt,
};

Map<String, Object?> assignment({
  String id = policeAssignmentId,
  String incidentId = firstIncidentId,
  required String organizationId,
  required String organizationKind,
  String status = 'PENDING',
}) => <String, Object?>{
  'id': id,
  'incident_id': incidentId,
  'target_organization_id': organizationId,
  'target_organization_kind': organizationKind,
  'status': status,
  'created_at': '2026-11-17T09:45:00Z',
  'updated_at': '2026-11-17T09:45:00Z',
};

ApiResponse pageResponse({
  required List<Map<String, Object?>> results,
  int? count,
  String? next,
}) => ApiResponse(
  statusCode: 200,
  body: jsonEncode(<String, Object?>{
    'count': count ?? results.length,
    'next': next,
    'previous': null,
    'results': results,
  }),
);

ApiResponse jsonApiResponse(int statusCode, Object body) => ApiResponse(
  statusCode: statusCode,
  body: body is String ? body : jsonEncode(body),
);
