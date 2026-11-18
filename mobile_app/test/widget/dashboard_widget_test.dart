import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/app.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

void main() {
  testWidgets(
    'role switching keeps police and hospital assignment data separate',
    (WidgetTester tester) async {
      final AuthHarness harness = await _dashboardHarness(
        profile: dashboardProfile(
          roles: const <String>['POLICE', 'HOSPITAL'],
          memberships: <Map<String, Object?>>[
            policeMembership(),
            hospitalMembership(),
          ],
        ),
        incidentHandler: (ApiRequest request) async {
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
      addTearDown(harness.close);

      await tester.pumpWidget(_app(harness));
      await tester.pumpAndSettle();

      expect(find.text('POLICE workspace'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Assigned police incidents'),
        200,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      expect(find.text('Assigned police incidents'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Central Police · Pending'),
        250,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      expect(find.text('Central Police · Pending'), findsOneWidget);
      expect(find.text('Central Hospital · Pending'), findsNothing);

      await tester.tap(find.byTooltip('Switch workspace'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('HOSPITAL workspace').last);
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Central Hospital · Pending'),
        250,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );

      expect(find.text('Assigned hospital incidents'), findsOneWidget);
      expect(find.text('Central Hospital · Pending'), findsOneWidget);
      expect(find.text('Central Police · Pending'), findsNothing);
    },
  );

  testWidgets(
    'organization selector filters locally and refreshes its context',
    (WidgetTester tester) async {
      final AuthHarness harness = await _dashboardHarness(
        profile: dashboardProfile(
          memberships: <Map<String, Object?>>[
            policeMembership(),
            policeMembership(
              id: secondPoliceOrganizationId,
              name: 'West Police',
              code: 'west-police',
            ),
          ],
        ),
        incidentHandler: (ApiRequest request) async {
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
      addTearDown(harness.close);

      await tester.pumpWidget(_app(harness));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Central Police · Pending'),
        250,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      expect(find.text('Central Police · Pending'), findsOneWidget);
      expect(find.text('West Police · Pending'), findsOneWidget);

      await tester.scrollUntilVisible(
        find.text('Filter this view by membership'),
        150,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      await tester.tap(find.byType(DropdownButton<String?>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('West Police · west-police').last);
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('West Police · Pending'),
        150,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );

      expect(find.text('West Police · Pending'), findsOneWidget);
      expect(find.text('Central Police · Pending'), findsNothing);
      expect(
        harness.transport.requests
            .where(
              (ApiRequest request) => request.uri.path.contains('/incidents/'),
            )
            .every(
              (ApiRequest request) =>
                  !request.uri.queryParameters.containsKey('organization_id'),
            ),
        isTrue,
      );
    },
  );

  testWidgets('assignment pagination beyond 100 rows is disclosed', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(),
      incidentHandler: (ApiRequest request) async {
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
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    final Finder scrollable = find
        .descendant(
          of: find.byType(RefreshIndicator),
          matching: find.byType(Scrollable),
        )
        .first;
    await tester.scrollUntilVisible(
      find.textContaining('continue beyond the bounded API page'),
      180,
      scrollable: scrollable,
    );

    expect(
      find.textContaining('continue beyond the bounded API page'),
      findsOneWidget,
    );
  });

  testWidgets('dashboard error has a retry path', (WidgetTester tester) async {
    int incidentRequests = 0;
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(),
      incidentHandler: (ApiRequest request) async {
        if (request.uri.path.endsWith('/incidents/')) {
          incidentRequests++;
          if (incidentRequests == 1) {
            return jsonApiResponse(503, <String, Object?>{
              'code': 'service_unavailable',
              'detail': 'private backend detail',
            });
          }
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
          );
        }
        throw StateError('Unexpected request path.');
      },
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Dashboard data unavailable'),
      200,
      scrollable: find
          .descendant(
            of: find.byType(RefreshIndicator),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('Dashboard data unavailable'), findsOneWidget);
    expect(find.textContaining('private backend detail'), findsNothing);

    await tester.ensureVisible(find.text('Try again'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Incident · 732dfcb2'),
      250,
      scrollable: find
          .descendant(
            of: find.byType(RefreshIndicator),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('Incident · 732dfcb2'), findsOneWidget);
  });

  testWidgets('unknown roles show a safe workspace state and retain logout', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(
        roles: const <String>['AI_SERVICE', 'UNKNOWN'],
        memberships: const <Map<String, Object?>>[],
      ),
      incidentHandler: (ApiRequest request) async =>
          throw StateError('Unknown roles must not read dashboard endpoints.'),
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('This account has no supported human workspace.'),
      findsOneWidget,
    );
    expect(find.text('Sign out'), findsOneWidget);
    expect(
      harness.transport.requests.any(
        (ApiRequest request) => request.uri.path.endsWith('/incidents/'),
      ),
      isFalse,
    );

    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in to ResQVision'), findsOneWidget);
  });

  testWidgets('admin workspace shows only backend scope and no global totals', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(
        roles: const <String>['ADMIN'],
        memberships: const <Map<String, Object?>>[],
      ),
      incidentHandler: (ApiRequest request) async {
        if (request.uri.path.endsWith('/incidents/')) {
          return pageResponse(results: const <Map<String, Object?>>[]);
        }
        throw StateError('No nested assignment request is expected.');
      },
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    expect(find.text('ADMIN workspace'), findsOneWidget);
    expect(
      find.textContaining('No system-wide summary API is available.'),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('No incidents in your authorized scope'),
      150,
      scrollable: find
          .descendant(
            of: find.byType(RefreshIndicator),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('No incidents in your authorized scope'), findsOneWidget);
    expect(find.textContaining('Total incidents'), findsNothing);
    expect(
      harness.transport.requests.any(
        (ApiRequest request) => request.uri.path.endsWith('/incidents/'),
      ),
      isTrue,
    );
  });

  testWidgets('police role without an active police membership is unavailable', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(
        roles: const <String>['POLICE'],
        memberships: const <Map<String, Object?>>[],
      ),
      incidentHandler: (ApiRequest request) async => throw StateError(
        'Dashboard API must not be called without membership.',
      ),
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text(
        'This role has no active matching organization membership. Contact your organization administrator.',
      ),
      150,
      scrollable: find
          .descendant(
            of: find.byType(RefreshIndicator),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('Workspace unavailable'), findsOneWidget);
    expect(
      harness.transport.requests.any(
        (ApiRequest request) => request.uri.path.endsWith('/incidents/'),
      ),
      isFalse,
    );
  });

  testWidgets('profile navigation shows the backend profile and memberships', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(),
      incidentHandler: (ApiRequest request) async =>
          pageResponse(results: const <Map<String, Object?>>[]),
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Profile').last);
    await tester.pumpAndSettle();

    expect(find.text('Rajat Reviewer'), findsOneWidget);
    expect(find.text('reviewer@example.test'), findsOneWidget);
    expect(find.text('Central Police'), findsOneWidget);
    expect(find.text('Sign out'), findsOneWidget);
  });

  testWidgets('narrow mobile layout uses bottom navigation without overflow', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final AuthHarness harness = await _dashboardHarness(
      profile: dashboardProfile(),
      incidentHandler: (ApiRequest request) async =>
          pageResponse(results: const <Map<String, Object?>>[]),
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Profile').last);
    await tester.pumpAndSettle();
    expect(find.text('Rajat Reviewer'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

Future<AuthHarness> _dashboardHarness({
  required Map<String, Object?> profile,
  required Future<ApiResponse> Function(ApiRequest request) incidentHandler,
}) async {
  final AuthHarness harness = AuthHarness(
    transport: ScriptedTransport((ApiRequest request) async {
      if (request.uri.path.endsWith('/auth/me/')) {
        return jsonApiResponse(200, profile);
      }
      if (request.uri.path.endsWith('/auth/logout/')) {
        return jsonApiResponse(204, '');
      }
      return incidentHandler(request);
    }),
  );
  harness.storage.tokens = AuthTokens.fromJson(loginTokens);
  await harness.session.restoreSession();
  return harness;
}

ResQVisionApp _app(AuthHarness harness) => ResQVisionApp(
  config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
  sessionController: harness.session,
  dashboardRepository: harness.dashboardRepository,
);
