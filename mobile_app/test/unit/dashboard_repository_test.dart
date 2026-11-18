import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

void main() {
  test(
    'police data includes only assignments for active police memberships',
    () async {
      final Map<String, Object?> profile = dashboardProfile(
        roles: const <String>['POLICE', 'HOSPITAL'],
        memberships: <Map<String, Object?>>[
          policeMembership(),
          hospitalMembership(),
        ],
      );
      final AuthHarness harness = await _authenticatedHarness(
        profile: profile,
        respond: (ApiRequest request) async {
          if (request.uri.path.endsWith('/incidents/')) {
            return pageResponse(results: <Map<String, Object?>>[incident()]);
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
          throw StateError('Unexpected request path.');
        },
      );
      try {
        final user = harness.session.user!;
        final DashboardPage page = await harness.dashboardRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: user.memberships,
          organizationId: null,
        );

        expect(page.totalCount, 1);
        expect(page.incidents, hasLength(1));
        expect(page.incidents.single.assignments, hasLength(1));
        expect(
          page.incidents.single.assignments.single.organizationKind,
          'POLICE',
        );
        expect(
          page.incidents.single.assignments.single.organizationName,
          'Central Police',
        );
        expect(
          harness.transport.requests.every(
            (ApiRequest request) =>
                request.headers['Authorization'] == 'Bearer access-one',
          ),
          isTrue,
        );
        expect(
          harness.transport.requests.map(
            (ApiRequest request) => request.uri.path,
          ),
          containsAll(<String>[
            '/api/v1/auth/me/',
            '/api/v1/incidents/',
            '/api/v1/incidents/$firstIncidentId/assignments/',
          ]),
        );
      } finally {
        harness.close();
      }
    },
  );

  test(
    'organization selection filters locally without sending an organization claim',
    () async {
      final Map<String, Object?> profile = dashboardProfile(
        memberships: <Map<String, Object?>>[
          policeMembership(),
          policeMembership(
            id: secondPoliceOrganizationId,
            name: 'West Police',
            code: 'west-police',
          ),
        ],
      );
      final AuthHarness harness = await _authenticatedHarness(
        profile: profile,
        respond: (ApiRequest request) async {
          if (request.uri.path.endsWith('/incidents/')) {
            return pageResponse(results: <Map<String, Object?>>[incident()]);
          }
          if (request.uri.path.endsWith('/assignments/')) {
            return pageResponse(
              results: <Map<String, Object?>>[
                assignment(
                  organizationId: policeOrganizationId,
                  organizationKind: 'POLICE',
                ),
                assignment(
                  id: '169172bd-b907-459d-9a57-78bb2ff3755c',
                  organizationId: secondPoliceOrganizationId,
                  organizationKind: 'POLICE',
                ),
              ],
            );
          }
          throw StateError('Unexpected request path.');
        },
      );
      try {
        final DashboardPage page = await harness.dashboardRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: harness.session.user!.memberships,
          organizationId: secondPoliceOrganizationId,
        );

        expect(page.incidents.single.assignments, hasLength(1));
        expect(
          page.incidents.single.assignments.single.organizationName,
          'West Police',
        );
        expect(
          harness.transport.requests
              .where(
                (ApiRequest request) =>
                    request.uri.path.contains('/incidents/'),
              )
              .every(
                (ApiRequest request) =>
                    !request.uri.queryParameters.containsKey('organization_id'),
              ),
          isTrue,
        );
      } finally {
        harness.close();
      }
    },
  );

  test('inactive memberships cannot open role scoped dashboard data', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(
        roles: const <String>['HOSPITAL'],
        memberships: <Map<String, Object?>>[
          hospitalMembership(status: 'SUSPENDED'),
        ],
      ),
      respond: (ApiRequest request) async =>
          throw StateError('Dashboard API must not be called.'),
    );
    try {
      await expectLater(
        harness.dashboardRepository.loadPage(
          role: DashboardRole.hospital,
          activeMemberships: harness.session.user!.memberships,
          organizationId: null,
        ),
        throwsA(isA<DashboardDataException>()),
      );
      expect(
        harness.transport.requests.any(
          (ApiRequest request) => request.uri.path.endsWith('/incidents/'),
        ),
        isFalse,
      );
    } finally {
      harness.close();
    }
  });

  test('incident pagination honors the backend next offset', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(),
      respond: (ApiRequest request) async {
        if (request.uri.path.endsWith('/incidents/')) {
          if (request.uri.queryParameters['offset'] == '5') {
            return pageResponse(
              results: <Map<String, Object?>>[
                incident(id: secondIncidentId, status: 'RESOLVED'),
              ],
              count: 6,
            );
          }
          return pageResponse(
            results: <Map<String, Object?>>[incident()],
            count: 6,
            next: 'http://127.0.0.1:8000/api/v1/incidents/?limit=5&offset=5',
          );
        }
        if (request.uri.path.endsWith('/assignments/')) {
          final String incidentId = request.uri.path.contains(secondIncidentId)
              ? secondIncidentId
              : firstIncidentId;
          return pageResponse(
            results: <Map<String, Object?>>[
              assignment(
                incidentId: incidentId,
                organizationId: policeOrganizationId,
                organizationKind: 'POLICE',
              ),
            ],
          );
        }
        throw StateError('Unexpected request path.');
      },
    );
    try {
      final firstPage = await harness.dashboardRepository.loadPage(
        role: DashboardRole.police,
        activeMemberships: harness.session.user!.memberships,
        organizationId: null,
      );
      final secondPage = await harness.dashboardRepository.loadPage(
        role: DashboardRole.police,
        activeMemberships: harness.session.user!.memberships,
        organizationId: null,
        offset: firstPage.nextOffset,
      );

      expect(firstPage.hasMore, isTrue);
      expect(firstPage.nextOffset, 5);
      expect(secondPage.hasMore, isFalse);
      expect(secondPage.incidents.single.id, secondIncidentId);
      expect(
        harness.transport.requests
            .where(
              (ApiRequest request) => request.uri.path.endsWith('/incidents/'),
            )
            .map((ApiRequest request) => request.uri.queryParameters['offset']),
        containsAll(<String>['0', '5']),
      );
    } finally {
      harness.close();
    }
  });

  test(
    'incident continuation requires a forward offset from backend metadata',
    () async {
      final AuthHarness harness = await _authenticatedHarness(
        profile: dashboardProfile(),
        respond: (ApiRequest request) async {
          if (request.uri.path.endsWith('/incidents/')) {
            return pageResponse(
              results: <Map<String, Object?>>[incident()],
              count: 2,
              next: 'http://127.0.0.1:8000/api/v1/incidents/?limit=5',
            );
          }
          throw StateError(
            'Assignments must not load after invalid page metadata.',
          );
        },
      );
      try {
        await expectLater(
          harness.dashboardRepository.loadPage(
            role: DashboardRole.police,
            activeMemberships: harness.session.user!.memberships,
            organizationId: null,
          ),
          throwsA(isA<DashboardDataException>()),
        );
        expect(
          harness.transport.requests.where(
            (ApiRequest request) => request.uri.path.endsWith('/assignments/'),
          ),
          isEmpty,
        );
      } finally {
        harness.close();
      }
    },
  );

  test(
    'missing incident next metadata does not estimate a continuation offset',
    () async {
      final AuthHarness harness = await _authenticatedHarness(
        profile: dashboardProfile(),
        respond: (ApiRequest request) async {
          if (request.uri.path.endsWith('/incidents/')) {
            return pageResponse(
              results: <Map<String, Object?>>[incident()],
              count: 42,
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
          throw StateError('Unexpected request path.');
        },
      );
      try {
        final DashboardPage page = await harness.dashboardRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: harness.session.user!.memberships,
          organizationId: null,
          offset: 10,
        );

        expect(page.hasMore, isFalse);
        expect(page.nextOffset, 10);
      } finally {
        harness.close();
      }
    },
  );

  test(
    'assignment next metadata marks the bounded 100-row page as partial',
    () async {
      final AuthHarness harness = await _authenticatedHarness(
        profile: dashboardProfile(),
        respond: (ApiRequest request) async {
          if (request.uri.path.endsWith('/incidents/')) {
            return pageResponse(results: <Map<String, Object?>>[incident()]);
          }
          if (request.uri.path.endsWith('/assignments/')) {
            return pageResponse(
              results: <Map<String, Object?>>[
                assignment(
                  organizationId: policeOrganizationId,
                  organizationKind: 'POLICE',
                ),
              ],
              count: 101,
              next:
                  'http://127.0.0.1:8000/api/v1/incidents/$firstIncidentId/assignments/?limit=100&offset=100',
            );
          }
          throw StateError('Unexpected request path.');
        },
      );
      try {
        final DashboardPage page = await harness.dashboardRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: harness.session.user!.memberships,
          organizationId: null,
        );

        expect(page.isPartial, isTrue);
        expect(page.incidents.single.assignments, hasLength(1));
        final ApiRequest assignmentRequest = harness.transport.requests
            .singleWhere(
              (ApiRequest request) =>
                  request.uri.path.endsWith('/assignments/'),
            );
        expect(assignmentRequest.uri.queryParameters['limit'], '100');
        expect(assignmentRequest.uri.queryParameters['offset'], '0');
        expect(
          harness.transport.requests.where(
            (ApiRequest request) => request.uri.path.endsWith('/assignments/'),
          ),
          hasLength(1),
          reason:
              'The page is bounded and the UI must disclose the returned next link.',
        );
      } finally {
        harness.close();
      }
    },
  );

  test('403 responses map to a safe access message', () async {
    final AuthHarness harness = await _authenticatedHarness(
      profile: dashboardProfile(),
      respond: (ApiRequest request) async =>
          jsonApiResponse(403, <String, Object?>{
            'code': 'forbidden',
            'detail': 'private backend policy detail',
          }),
    );
    try {
      await expectLater(
        harness.dashboardRepository.loadPage(
          role: DashboardRole.police,
          activeMemberships: harness.session.user!.memberships,
          organizationId: null,
        ),
        throwsA(
          isA<DashboardDataException>().having(
            (DashboardDataException error) => error.message,
            'message',
            'You do not have access to this operational data.',
          ),
        ),
      );
    } finally {
      harness.close();
    }
  });
}

Future<AuthHarness> _authenticatedHarness({
  required Map<String, Object?> profile,
  required Future<ApiResponse> Function(ApiRequest request) respond,
}) async {
  final AuthHarness harness = AuthHarness(
    transport: ScriptedTransport((ApiRequest request) async {
      if (request.uri.path.endsWith('/auth/me/')) {
        return jsonApiResponse(200, profile);
      }
      return respond(request);
    }),
  );
  harness.storage.tokens = AuthTokens.fromJson(loginTokens);
  await harness.session.restoreSession();
  return harness;
}
