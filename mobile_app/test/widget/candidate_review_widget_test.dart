import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/theme/app_theme.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/dashboard/presentation/dashboard_shell.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

const String candidateId = 'd02d1746-2cbc-4ac8-b409-0b99e38c7801';

void main() {
  testWidgets('Police reviewer can start and verify an assigned candidate', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(800, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    bool started = false;
    bool verified = false;
    int verificationAttempts = 0;
    final AuthHarness harness = await _reviewHarness(
      onRequest: (ApiRequest request) async {
        if (request.uri.path == '/api/v1/candidates/') {
          return pageResponse(
            results: <Map<String, Object?>>[
              _candidate(
                status: verified
                    ? 'VERIFIED'
                    : started
                    ? 'UNDER_REVIEW'
                    : 'RECEIVED',
              ),
            ],
          );
        }
        if (request.uri.path == '/api/v1/candidates/$candidateId/') {
          return jsonApiResponse(
            200,
            _candidate(
              status: verified
                  ? 'VERIFIED'
                  : started
                  ? 'UNDER_REVIEW'
                  : 'RECEIVED',
            ),
          );
        }
        if (request.uri.path == '/api/v1/candidates/$candidateId/review/') {
          started = true;
          return _commandResponse(_candidate(status: 'UNDER_REVIEW'));
        }
        if (request.uri.path == '/api/v1/candidates/$candidateId/verify/') {
          verified = true;
          verificationAttempts++;
          if (verificationAttempts == 1) {
            return jsonApiResponse(503, <String, Object?>{
              'code': 'service_unavailable',
              'detail': 'Try again.',
            });
          }
          return _commandResponse(incident(status: 'OPEN'));
        }
        return _dashboardResponse(request);
      },
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Candidates').last);
    await tester.pumpAndSettle();

    expect(find.text('Assigned candidate review'), findsOneWidget);
    expect(find.textContaining('Candidate · d02d1746'), findsOneWidget);
    await tester.tap(find.textContaining('Candidate · d02d1746'));
    await tester.pumpAndSettle();
    expect(find.text('Start review'), findsOneWidget);

    await tester.tap(find.text('Start review'));
    await tester.pumpAndSettle();
    expect(started, isTrue);
    expect(find.text('Verify candidate'), findsOneWidget);

    await tester.tap(find.text('Verify candidate'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Verify').last);
    await tester.pumpAndSettle();
    expect(find.text('Retry verification'), findsOneWidget);
    expect(find.textContaining('temporarily unavailable'), findsOneWidget);

    await tester.tap(find.text('Retry verification'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Verify').last);
    await tester.pumpAndSettle();

    expect(verified, isTrue);
    expect(find.text('Candidate · d02d1746'), findsOneWidget);
    expect(find.text('Verified'), findsOneWidget);
    final ApiRequest startRequest = harness.transport.requests.singleWhere(
      (ApiRequest request) =>
          request.uri.path == '/api/v1/candidates/$candidateId/review/',
    );
    expect(startRequest.method, 'POST');
    expect(_uuidPattern.hasMatch(_commandId(startRequest)), isTrue);
    final List<ApiRequest> verifyRequests = harness.transport.requests
        .where(
          (ApiRequest request) =>
              request.uri.path == '/api/v1/candidates/$candidateId/verify/',
        )
        .toList();
    expect(verifyRequests, hasLength(2));
    expect(
      verifyRequests.every((ApiRequest request) => request.method == 'POST'),
      isTrue,
    );
    expect(_uuidPattern.hasMatch(_commandId(verifyRequests.first)), isTrue);
    expect(_commandId(verifyRequests.last), _commandId(verifyRequests.first));
    expect(
      harness.transport.requests.any(
        (ApiRequest request) => request.uri.path == '/api/v1/incidents/',
      ),
      isTrue,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Police candidate actions stay hidden without active membership',
    (WidgetTester tester) async {
      final AuthHarness harness = await _reviewHarness(
        profile: dashboardProfile(
          memberships: <Map<String, Object?>>[
            policeMembership(status: 'SUSPENDED'),
          ],
        ),
      );
      addTearDown(harness.close);

      await tester.pumpWidget(_app(harness));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Candidates').last);
      await tester.pumpAndSettle();

      expect(find.text('Police membership required'), findsOneWidget);
      expect(
        harness.transport.requests.any(
          (ApiRequest request) => request.uri.path == '/api/v1/candidates/',
        ),
        isFalse,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Police reviewer rejects a candidate with a required rationale', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(800, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final AuthHarness harness = await _reviewHarness(
      onRequest: (ApiRequest request) async {
        if (request.uri.path == '/api/v1/candidates/') {
          return pageResponse(results: <Map<String, Object?>>[
            _candidate(status: 'REJECTED'),
          ]);
        }
        if (request.uri.path == '/api/v1/candidates/$candidateId/') {
          return jsonApiResponse(200, _candidate(status: 'UNDER_REVIEW'));
        }
        if (request.uri.path == '/api/v1/candidates/$candidateId/reject/') {
          return _commandResponse(_candidate(status: 'REJECTED'));
        }
        return _dashboardResponse(request);
      },
    );
    addTearDown(harness.close);

    await tester.pumpWidget(_app(harness));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Candidates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('Candidate · d02d1746'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Reject candidate'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextField),
      'The observation does not establish an accident.',
    );
    await tester.tap(find.text('Reject').last);
    await tester.pumpAndSettle();

    expect(find.text('Rejected'), findsOneWidget);
    final ApiRequest rejectRequest = harness.transport.requests.singleWhere(
      (ApiRequest request) =>
          request.uri.path == '/api/v1/candidates/$candidateId/reject/',
    );
    expect(rejectRequest.method, 'POST');
    expect(_commandId(rejectRequest), matches(_uuidPattern));
    expect(
      (rejectRequest.jsonBody! as Map<String, Object?>)['rationale'],
      'The observation does not establish an accident.',
    );
    expect(
      harness.transport.requests.any(
        (ApiRequest request) =>
            request.uri.path == '/api/v1/candidates/$candidateId/verify/',
      ),
      isFalse,
    );
    expect(tester.takeException(), isNull);
  });
}

final RegExp _uuidPattern = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$',
);

String _commandId(ApiRequest request) {
  final Object? body = request.jsonBody;
  if (body is Map<String, Object?> && body['command_id'] is String) {
    return body['command_id']! as String;
  }
  return '';
}

Future<AuthHarness> _reviewHarness({
  Map<String, Object?>? profile,
  Future<ApiResponse> Function(ApiRequest request)? onRequest,
}) async {
  final AuthHarness harness = AuthHarness(
    transport: ScriptedTransport((ApiRequest request) async {
      if (request.uri.path == '/api/v1/auth/me/') {
        return jsonApiResponse(200, profile ?? dashboardProfile());
      }
      if (request.uri.path == '/api/v1/auth/logout/') {
        return jsonApiResponse(204, '');
      }
      if (onRequest != null) return onRequest(request);
      return _dashboardResponse(request);
    }),
  );
  harness.storage.tokens = AuthTokens.fromJson(loginTokens);
  await harness.session.restoreSession();
  return harness;
}

ApiResponse _dashboardResponse(ApiRequest request) {
  if (request.uri.path == '/api/v1/incidents/') {
    return pageResponse(results: const <Map<String, Object?>>[]);
  }
  if (request.uri.path.endsWith('/assignments/')) {
    return pageResponse(results: const <Map<String, Object?>>[]);
  }
  throw StateError('Unexpected request path: ${request.uri.path}');
}

Map<String, Object?> _candidate({required String status}) => <String, Object?>{
  'id': candidateId,
  'police_organization_id': policeOrganizationId,
  'status': status,
  'created_at': '2026-11-19T09:30:00Z',
  'updated_at': '2026-11-19T10:00:00Z',
};

ApiResponse _commandResponse(Map<String, Object?> data) =>
    jsonApiResponse(200, <String, Object?>{'data': data, 'replayed': false});

Widget _app(AuthHarness harness) => MaterialApp(
  theme: AppTheme.light,
  home: DashboardShell(
    session: harness.session,
    user: harness.session.user!,
    repository: harness.dashboardRepository,
    incidentRepository: harness.incidentRepository,
    candidateReviewRepository: harness.candidateReviewRepository,
  ),
);
