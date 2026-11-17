import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/networking/authenticated_api_client.dart';
import 'package:resqvision_mobile/features/authentication/application/auth_session_controller.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_failure.dart';

import '../support/auth_test_support.dart';

void main() {
  test(
    'concurrent 401 responses share one refresh and replay with rotated credentials',
    () async {
      final Completer<void> refreshStarted = Completer<void>();
      final Completer<ApiResponse> finishRefresh = Completer<ApiResponse>();
      var refreshCount = 0;
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          refreshCount++;
          if (!refreshStarted.isCompleted) refreshStarted.complete();
          return finishRefresh.future;
        }
        if (request.uri.path.endsWith('/protected/read/')) {
          if (request.headers['Authorization'] == 'Bearer access-one') {
            return jsonResponse(
              401,
              '{"code":"authentication_failed","detail":"safe"}',
            );
          }
          return jsonResponse(200, '{"ok":true}');
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );
      final AuthenticatedApiClient client = AuthenticatedApiClient(
        apiClient: harness.apiClient,
        session: harness.session,
      );

      final List<Future<ApiResponse>> pending =
          List<Future<ApiResponse>>.generate(
            6,
            (int index) => client.request(
              'GET',
              'protected/read/',
              headers: <String, String>{'X-Request-Label': 'read-$index'},
              jsonBody: <String, Object?>{'offset': index},
            ),
          );
      await refreshStarted.future;
      finishRefresh.complete(tokenResponse(rotatedTokens));
      final List<ApiResponse> responses = await Future.wait(pending);

      expect(
        responses.every((ApiResponse response) => response.statusCode == 200),
        isTrue,
      );
      expect(refreshCount, 1);
      expect(harness.storage.tokens?.access, 'access-two');
      expect(harness.storage.tokens?.refresh, 'refresh-two');
      final List<ApiRequest> replays = transport.requests
          .where(
            (ApiRequest request) =>
                request.uri.path.endsWith('/protected/read/') &&
                request.headers['Authorization'] == 'Bearer access-two',
          )
          .toList();
      expect(replays, hasLength(6));
      expect(
        replays.any(
          (ApiRequest request) =>
              request.jsonBody is Map<String, Object?> &&
              (request.jsonBody as Map<String, Object?>)['offset'] == 4,
        ),
        isTrue,
      );
      expect(
        replays.map((ApiRequest request) => request.headers['X-Request-Label']),
        contains('read-4'),
      );
      harness.close();
    },
  );

  test('403 and 429 responses do not start token refresh', () async {
    final ScriptedTransport transport = ScriptedTransport((
      ApiRequest request,
    ) async {
      if (request.uri.path.endsWith('/auth/token/')) {
        return tokenResponse(loginTokens);
      }
      if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
      if (request.uri.path.endsWith('/restricted/')) {
        return jsonResponse(403, '{}');
      }
      if (request.uri.path.endsWith('/limited/')) {
        return jsonResponse(429, '{}');
      }
      throw StateError('Unexpected request path.');
    });
    final AuthHarness harness = AuthHarness(transport: transport);
    await harness.session.login(
      email: 'reviewer@example.test',
      password: 'secret',
    );
    final AuthenticatedApiClient client = AuthenticatedApiClient(
      apiClient: harness.apiClient,
      session: harness.session,
    );

    expect((await client.request('GET', 'restricted/')).statusCode, 403);
    expect((await client.request('GET', 'limited/')).statusCode, 429);
    expect(
      transport.requests.where(
        (ApiRequest request) =>
            request.uri.path.endsWith('/auth/token/refresh/'),
      ),
      isEmpty,
    );
    harness.close();
  });

  test(
    'unsafe requests can refresh the session but are never automatically replayed',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          return tokenResponse(rotatedTokens);
        }
        if (request.uri.path.endsWith('/commands/')) {
          return jsonResponse(401, '{}');
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );
      final AuthenticatedApiClient client = AuthenticatedApiClient(
        apiClient: harness.apiClient,
        session: harness.session,
      );

      final ApiResponse response = await client.request(
        'POST',
        'commands/',
        jsonBody: <String, Object?>{'command_id': 'stable-command-id'},
      );

      expect(response.statusCode, 401);
      expect(harness.session.status, SessionStatus.authenticated);
      expect(
        transport.requests.where(
          (ApiRequest request) => request.uri.path.endsWith('/commands/'),
        ),
        hasLength(1),
      );
      harness.close();
    },
  );

  test(
    'refresh failure releases all waiters and preserves credentials on temporary errors',
    () async {
      final Completer<void> refreshStarted = Completer<void>();
      final Completer<ApiResponse> finishRefresh = Completer<ApiResponse>();
      var refreshCount = 0;
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          refreshCount++;
          if (!refreshStarted.isCompleted) refreshStarted.complete();
          return finishRefresh.future;
        }
        if (request.uri.path.endsWith('/protected/')) {
          return jsonResponse(401, '{}');
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );
      final AuthenticatedApiClient client = AuthenticatedApiClient(
        apiClient: harness.apiClient,
        session: harness.session,
      );
      final List<Future<ApiResponse>> pending =
          List<Future<ApiResponse>>.generate(
            4,
            (_) => client.request('GET', 'protected/'),
          );
      await refreshStarted.future;
      finishRefresh.complete(jsonResponse(503, '{}'));

      await expectLater(
        Future.wait(pending),
        throwsA(
          isA<AuthException>().having(
            (AuthException error) => error.failure,
            'failure',
            AuthFailure.server,
          ),
        ),
      );
      expect(refreshCount, 1);
      expect(harness.session.status, SessionStatus.authenticated);
      expect(harness.storage.tokens?.refresh, 'refresh-one');
      harness.close();
    },
  );

  test(
    'authentication endpoints are not wrapped in Authorization or refresh retries',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          return jsonResponse(
            401,
            jsonEncode(<String, Object?>{'code': 'authentication_failed'}),
          );
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );
      final AuthenticatedApiClient client = AuthenticatedApiClient(
        apiClient: harness.apiClient,
        session: harness.session,
      );

      final ApiResponse response = await client.request(
        'GET',
        'auth/token/refresh/',
      );
      final ApiRequest refreshRequest = transport.requests.last;
      expect(response.statusCode, 401);
      expect(refreshRequest.headers.containsKey('Authorization'), isFalse);
      expect(
        transport.requests.where(
          (ApiRequest request) =>
              request.uri.path.endsWith('/auth/token/refresh/'),
        ),
        hasLength(1),
      );
      harness.close();
    },
  );
}
