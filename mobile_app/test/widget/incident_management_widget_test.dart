import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';
import 'package:resqvision_mobile/features/incidents/presentation/incident_management_screen.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

void main() {
  testWidgets('incident list shows backend incident data', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _incidentHarness();
    addTearDown(harness.close);

    await tester.pumpWidget(_screen(harness));
    await tester.pumpAndSettle();

    expect(find.text('Police incidents'), findsOneWidget);
    expect(find.textContaining('Incident · 732dfcb2'), findsOneWidget);
    expect(find.text('Open'), findsOneWidget);
    expect(find.text('Candidate review unavailable'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'detail screen shows assignment and unavailable evidence/location',
    (WidgetTester tester) async {
      final AuthHarness harness = await _incidentHarness();
      addTearDown(harness.close);

      await tester.pumpWidget(_screen(harness));
      await tester.pumpAndSettle();
      await tester.tap(find.text('View details →'));
      await tester.pumpAndSettle();

      expect(find.text('Incident details'), findsOneWidget);
      expect(find.text('Central Police'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Location information unavailable'),
        180,
        scrollable: find.byType(Scrollable).last,
      );
      expect(find.text('Location information unavailable'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Evidence information unavailable'),
        180,
        scrollable: find.byType(Scrollable).last,
      );
      expect(find.text('Evidence information unavailable'), findsOneWidget);
      await tester.drag(find.byType(Scrollable).last, const Offset(0, 1200));
      await tester.pumpAndSettle();
      expect(
        find.textContaining('does not change incident state'),
        findsOneWidget,
      );
      expect(find.text('Resolve'), findsNothing);
      expect(find.text('Close incident'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('status filtering and load more follow backend pagination', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = await _incidentHarness(withNextPage: true);
    addTearDown(harness.close);

    await tester.pumpWidget(_screen(harness));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownButtonFormField<String?>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Response Active').last);
    await tester.pumpAndSettle();

    final ApiRequest filteredRequest = harness.transport.requests.singleWhere(
      (request) =>
          request.uri.path == '/api/v1/incidents/' &&
          request.uri.queryParameters['status'] == 'RESPONSE_ACTIVE',
    );
    expect(filteredRequest.uri.queryParameters['status'], 'RESPONSE_ACTIVE');
    expect(find.textContaining('Incident · ecc70b40'), findsOneWidget);
    expect(find.text('Load next page'), findsOneWidget);

    await tester.tap(find.text('Load next page'));
    await tester.pumpAndSettle();
    final List<ApiRequest> pageRequests = harness.transport.requests
        .where((request) => request.uri.path == '/api/v1/incidents/')
        .toList();
    expect(pageRequests.last.uri.queryParameters['offset'], '10');
    expect(pageRequests.last.uri.queryParameters['status'], 'RESPONSE_ACTIVE');
    expect(find.text('Load next page'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}

Future<AuthHarness> _incidentHarness({bool withNextPage = false}) async {
  final AuthHarness harness = AuthHarness(
    transport: ScriptedTransport((request) async {
      if (request.uri.path == '/api/v1/auth/me/') {
        return jsonApiResponse(200, dashboardProfile());
      }
      if (request.uri.path == '/api/v1/incidents/') {
        if (withNextPage && request.uri.queryParameters['offset'] == '10') {
          return pageResponse(
            results: const <Map<String, Object?>>[],
            count: 11,
          );
        }
        if (withNextPage && request.uri.queryParameters['status'] != null) {
          return pageResponse(
            results: <Map<String, Object?>>[
              incident(
                id: secondIncidentId,
                status: request.uri.queryParameters['status']!,
              ),
            ],
            count: 11,
            next:
                'http://127.0.0.1:8000/api/v1/incidents/?limit=10&offset=10&status=${request.uri.queryParameters['status']}',
          );
        }
        if (withNextPage) {
          return pageResponse(
            results: <Map<String, Object?>>[incident()],
            count: 11,
            next: 'http://127.0.0.1:8000/api/v1/incidents/?limit=10&offset=10',
          );
        }
        return pageResponse(results: <Map<String, Object?>>[incident()]);
      }
      if (request.uri.path == '/api/v1/incidents/$firstIncidentId/') {
        return jsonApiResponse(200, incident());
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
      throw StateError('Unexpected request path: ${request.uri.path}');
    }),
  );
  harness.storage.tokens = AuthTokens.fromJson(loginTokens);
  await harness.session.restoreSession();
  return harness;
}

Widget _screen(AuthHarness harness) => MaterialApp(
  home: IncidentManagementScreen(
    repository: harness.incidentRepository,
    role: DashboardRole.police,
    memberships: harness.session.user!.memberships,
    organizationId: null,
  ),
);
