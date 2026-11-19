import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';
import 'package:resqvision_mobile/features/incidents/data/incident_repository.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

void main() {
  test('status filter and backend continuation are sent as contracted', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(),
      respond: (ApiRequest request) async {
        if (request.uri.path == '/api/v1/incidents/') {
          return pageResponse(
            results: <Map<String, Object?>>[incident()],
            count: 11,
            next:
                'http://127.0.0.1:8000/api/v1/incidents/?limit=10&offset=10&status=OPEN',
          );
        }
        if (request.uri.path.endsWith('/assignments/')) {
          return pageResponse(
            results: <Map<String, Object?>>[
              assignment(
                organizationId: policeOrganizationId,
                organizationKind: 'POLICE',
              ),
            ],
          );
        }
        throw StateError('Unexpected request path: ${request.uri.path}');
      },
    );
    addTearDown(harness.close);

    final ManagedIncidentPage page = await harness.incidentRepository.loadPage(
      role: DashboardRole.police,
      activeMemberships: harness.session.user!.memberships,
      status: 'OPEN',
    );

    expect(page.incidents, hasLength(1));
    expect(page.incidents.single.status, 'OPEN');
    expect(page.incidents.single.assignments.single.organizationKind, 'POLICE');
    expect(page.totalCount, 11);
    expect(page.hasMore, isTrue);
    expect(page.nextOffset, 10);
    final ApiRequest request = harness.transport.requests.singleWhere(
      (ApiRequest item) => item.uri.path == '/api/v1/incidents/',
    );
    expect(request.uri.queryParameters, <String, String>{
      'limit': '10',
      'offset': '0',
      'status': 'OPEN',
    });
  });

  test(
    'detail includes only the selected role and active organization scope',
    () async {
      final AuthHarness harness = await _authenticatedHarness(
        profile: dashboardProfile(
          roles: const <String>['POLICE', 'HOSPITAL'],
          memberships: <Map<String, Object?>>[
            policeMembership(),
            hospitalMembership(),
          ],
        ),
        respond: (ApiRequest request) async {
          if (request.uri.path == '/api/v1/incidents/$firstIncidentId/') {
            return jsonApiResponse(200, incident());
          }
          if (request.uri.path.endsWith('/assignments/')) {
            return pageResponse(
              results: <Map<String, Object?>>[
                assignment(
                  organizationId: policeOrganizationId,
                  organizationKind: 'POLICE',
                ),
                assignment(
                  id: hospitalAssignmentId,
                  organizationId: hospitalOrganizationId,
                  organizationKind: 'HOSPITAL',
                ),
              ],
            );
          }
          throw StateError('Unexpected request path: ${request.uri.path}');
        },
      );
      addTearDown(harness.close);

      final ManagedIncidentDetail detail = await harness.incidentRepository
          .loadDetail(
            incidentId: firstIncidentId,
            role: DashboardRole.police,
            activeMemberships: harness.session.user!.memberships,
            organizationId: policeOrganizationId,
          );

      expect(detail.incident.id, firstIncidentId);
      expect(detail.assignments, hasLength(1));
      expect(detail.assignments.single.organizationKind, 'POLICE');
      expect(detail.assignments.single.organizationName, 'Central Police');
      expect(
        harness.transport.requests.map(
          (ApiRequest request) => request.uri.path,
        ),
        containsAll(<String>[
          '/api/v1/incidents/$firstIncidentId/',
          '/api/v1/incidents/$firstIncidentId/assignments/',
        ]),
      );
    },
  );

  test('inactive membership is rejected before requesting incidents', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(
        memberships: <Map<String, Object?>>[
          policeMembership(status: 'SUSPENDED'),
        ],
      ),
      respond: (ApiRequest request) async =>
          throw StateError('Incident API must not be called.'),
    );
    addTearDown(harness.close);

    await expectLater(
      harness.incidentRepository.loadPage(
        role: DashboardRole.police,
        activeMemberships: harness.session.user!.memberships,
      ),
      throwsA(isA<IncidentDataException>()),
    );
    expect(
      harness.transport.requests.any(
        (ApiRequest request) => request.uri.path == '/api/v1/incidents/',
      ),
      isFalse,
    );
  });

  test('403 response maps to a safe access-denied message', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(),
      respond: (ApiRequest request) async => jsonApiResponse(
        403,
        <String, Object?>{'code': 'forbidden', 'detail': 'private policy data'},
      ),
    );
    addTearDown(harness.close);

    await expectLater(
      harness.incidentRepository.loadPage(
        role: DashboardRole.police,
        activeMemberships: harness.session.user!.memberships,
      ),
      throwsA(
        isA<IncidentDataException>().having(
          (IncidentDataException error) => error.message,
          'message',
          'You do not have access to this incident data.',
        ),
      ),
    );
  });

  test(
    'policy-blocked 503 is reported without exposing backend detail',
    () async {
      final AuthHarness harness = await _authenticatedHarness(
        profile: dashboardProfile(),
        respond: (ApiRequest request) async =>
            jsonApiResponse(503, <String, Object?>{
              'code': 'policy_unavailable',
              'detail': 'secret internal policy description',
            }),
      );
      addTearDown(harness.close);

      await expectLater(
        harness.incidentRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: harness.session.user!.memberships,
        ),
        throwsA(
          isA<IncidentDataException>()
              .having(
                (IncidentDataException error) => error.message,
                'message',
                contains('backend policy is pending approval'),
              )
              .having(
                (IncidentDataException error) => error.message,
                'message',
                isNot(contains('secret internal')),
              ),
        ),
      );
    },
  );
}

Future<AuthHarness> _authenticatedHarness({
  required Map<String, Object?> profile,
  required Future<ApiResponse> Function(ApiRequest request) respond,
}) async {
  final AuthHarness harness = AuthHarness(
    transport: ScriptedTransport((ApiRequest request) async {
      if (request.uri.path == '/api/v1/auth/me/') {
        return jsonApiResponse(200, profile);
      }
      return respond(request);
    }),
  );
  harness.storage.tokens = AuthTokens.fromJson(loginTokens);
  await harness.session.restoreSession();
  return harness;
}
