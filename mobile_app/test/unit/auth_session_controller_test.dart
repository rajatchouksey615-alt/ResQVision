import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/authenticated_api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/authentication/application/auth_session_controller.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_failure.dart';

import '../support/auth_test_support.dart';

void main() {
  test(
    'login persists only token credentials and loads identity from the backend',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);

      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'not-saved-password',
      );

      expect(harness.session.status, SessionStatus.authenticated);
      expect(harness.session.user?.email, 'reviewer@example.test');
      expect(harness.session.user?.availableRoles, <String>['POLICE']);
      expect(harness.storage.tokens?.access, 'access-one');
      expect(harness.storage.tokens?.refresh, 'refresh-one');
      expect(harness.storage.tokens, isNotNull);
      harness.close();
    },
  );

  test(
    'startup validates profile and persists refresh-token rotation',
    () async {
      final MemoryTokenStorage storage = MemoryTokenStorage()
        ..tokens = const AuthTokens(
          access: 'access-one',
          refresh: 'refresh-one',
        );
      int profileCalls = 0;
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/me/')) {
          profileCalls++;
          if (profileCalls == 1) {
            return jsonResponse(
              401,
              '{"code":"authentication_failed","detail":"safe"}',
            );
          }
          return profileResponse();
        }
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          return tokenResponse(rotatedTokens);
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(
        transport: transport,
        storage: storage,
      );

      await harness.session.restoreSession();

      expect(harness.session.status, SessionStatus.authenticated);
      expect(harness.session.user?.id, 'fbdc2770-2bcd-427b-9856-ef8e73d46752');
      expect(storage.tokens?.access, 'access-two');
      expect(storage.tokens?.refresh, 'refresh-two');
      expect(storage.writes, hasLength(1));
      expect(
        transport.requests.map((ApiRequest request) => request.uri.path),
        <String>[
          '/api/v1/auth/me/',
          '/api/v1/auth/token/refresh/',
          '/api/v1/auth/me/',
        ],
      );
      harness.close();
    },
  );

  test(
    'invalid refresh credentials clear local credentials and expire the session',
    () async {
      final MemoryTokenStorage storage = MemoryTokenStorage()
        ..tokens = const AuthTokens(
          access: 'access-one',
          refresh: 'refresh-one',
        );
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        return jsonResponse(
          401,
          '{"code":"authentication_failed","detail":"safe"}',
        );
      });
      final AuthHarness harness = AuthHarness(
        transport: transport,
        storage: storage,
      );

      await harness.session.restoreSession();

      expect(harness.session.status, SessionStatus.sessionExpired);
      expect(harness.session.user, isNull);
      expect(storage.tokens, isNull);
      harness.close();
    },
  );

  test(
    'temporary startup failure retains credentials and allows retry',
    () async {
      final MemoryTokenStorage storage = MemoryTokenStorage()
        ..tokens = const AuthTokens(
          access: 'access-one',
          refresh: 'refresh-one',
        );
      bool unavailable = true;
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/me/') && unavailable) {
          throw TimeoutException('private host detail');
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(
        transport: transport,
        storage: storage,
      );

      await harness.session.restoreSession();
      expect(harness.session.status, SessionStatus.recoverableError);
      expect(storage.tokens?.refresh, 'refresh-one');
      expect(harness.session.error?.message, isNot(contains('private')));

      unavailable = false;
      await harness.session.restoreSession();
      expect(harness.session.status, SessionStatus.authenticated);
      expect(harness.session.user?.email, 'reviewer@example.test');
      harness.close();
    },
  );

  test('secure storage failure prevents persistent sign-in', () async {
    final MemoryTokenStorage storage = MemoryTokenStorage()..failWrites = true;
    final ScriptedTransport transport = ScriptedTransport((
      ApiRequest request,
    ) async {
      if (request.uri.path.endsWith('/auth/token/')) {
        return tokenResponse(loginTokens);
      }
      throw StateError('Profile must not load when tokens cannot be saved.');
    });
    final AuthHarness harness = AuthHarness(
      transport: transport,
      storage: storage,
    );

    await harness.session.login(
      email: 'reviewer@example.test',
      password: 'secret',
    );

    expect(harness.session.status, SessionStatus.unauthenticated);
    expect(harness.session.user, isNull);
    expect(storage.tokens, isNull);
    expect(harness.session.error?.message, contains('Secure session storage'));
    harness.close();
  });

  test(
    'logout clears device credentials and calls the backend revocation contract',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/logout/')) {
          expect(request.method, 'POST');
          expect(request.headers['Authorization'], 'Bearer access-one');
          expect(request.jsonBody, <String, Object?>{'refresh': 'refresh-one'});
          return jsonResponse(204, '');
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );

      final result = await harness.session.logout();

      expect(result.localCredentialsCleared, isTrue);
      expect(result.serverRevocationConfirmed, isTrue);
      expect(harness.session.status, SessionStatus.unauthenticated);
      expect(harness.session.user, isNull);
      expect(harness.storage.tokens, isNull);
      harness.close();
    },
  );

  test(
    'logout during refresh revokes the replacement and stale work cannot restore session',
    () async {
      final Completer<void> refreshStarted = Completer<void>();
      final Completer<ApiResponse> completeRefresh = Completer<ApiResponse>();
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return tokenResponse(loginTokens);
        }
        if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
        if (request.uri.path.endsWith('/auth/token/refresh/')) {
          if (!refreshStarted.isCompleted) refreshStarted.complete();
          return completeRefresh.future;
        }
        if (request.uri.path.endsWith('/auth/logout/')) {
          expect(request.headers['Authorization'], 'Bearer access-two');
          expect(request.jsonBody, <String, Object?>{'refresh': 'refresh-two'});
          return jsonResponse(204, '');
        }
        if (request.uri.path.endsWith('/protected/')) {
          return jsonResponse(
            401,
            '{"code":"authentication_failed","detail":"safe"}',
          );
        }
        throw StateError('Unexpected request path.');
      });
      final AuthHarness harness = AuthHarness(transport: transport);
      await harness.session.login(
        email: 'reviewer@example.test',
        password: 'secret',
      );
      final AuthenticatedApiClient authenticated = AuthenticatedApiClient(
        apiClient: harness.apiClient,
        session: harness.session,
      );
      final Future<ApiResponse> protectedRequest = authenticated.request(
        'GET',
        'protected/',
      );
      await refreshStarted.future;
      final Future<LogoutResult> logout = harness.session.logout();
      completeRefresh.complete(tokenResponse(rotatedTokens));

      await expectLater(protectedRequest, throwsA(isA<AuthException>()));
      final result = await logout;

      expect(result.serverRevocationConfirmed, isTrue);
      expect(harness.session.status, SessionStatus.unauthenticated);
      expect(harness.session.user, isNull);
      expect(harness.storage.tokens, isNull);
      harness.close();
    },
  );
}
