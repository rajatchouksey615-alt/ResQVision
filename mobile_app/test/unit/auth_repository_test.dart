import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_failure.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_repository.dart';
import 'package:resqvision_mobile/features/authentication/data/models/authenticated_user.dart';

import '../support/auth_test_support.dart';

void main() {
  test(
    'login sends canonical email and unchanged password without a Bearer token',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        expect(request.method, 'POST');
        expect(request.uri.path, '/api/v1/auth/token/');
        expect(request.headers.containsKey('Authorization'), isFalse);
        expect(request.jsonBody, <String, Object?>{
          'email': 'reviewer@example.test',
          'password': ' secret with spaces ',
        });
        return tokenResponse(loginTokens);
      });
      final ApiClient client = _client(transport);
      final AuthRepository repository = AuthRepository(apiClient: client);

      final AuthTokens tokens = await repository.login(
        email: ' Reviewer@Example.Test ',
        password: ' secret with spaces ',
      );

      expect(tokens.access, 'access-one');
      expect(tokens.refresh, 'refresh-one');
      client.close();
    },
  );

  test(
    'refresh sends only refresh credentials and parses the rotated pair',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        expect(request.uri.path, '/api/v1/auth/token/refresh/');
        expect(request.headers.containsKey('Authorization'), isFalse);
        expect(request.jsonBody, <String, Object?>{'refresh': 'refresh-one'});
        return tokenResponse(rotatedTokens);
      });
      final ApiClient client = _client(transport);

      final AuthTokens tokens = await AuthRepository(
        apiClient: client,
      ).refresh('refresh-one');

      expect(tokens.access, 'access-two');
      expect(tokens.refresh, 'refresh-two');
      client.close();
    },
  );

  test(
    'current-user parsing preserves backend roles and active memberships',
    () async {
      final ScriptedTransport transport = ScriptedTransport((
        ApiRequest request,
      ) async {
        expect(request.uri.path, '/api/v1/auth/me/');
        expect(request.headers['Authorization'], 'Bearer access-one');
        return profileResponse();
      });
      final ApiClient client = _client(transport);

      final AuthenticatedUser user = await AuthRepository(
        apiClient: client,
      ).currentUser('access-one');

      expect(user.displayName, 'Rajat Reviewer');
      expect(user.availableRoles, <String>['POLICE']);
      expect(user.memberships.single.organizationName, 'Central Police');
      expect(user.memberships.single.status, 'ACTIVE');
      client.close();
    },
  );

  test('safe authentication errors never expose raw server details', () async {
    final ScriptedTransport transport = ScriptedTransport((
      ApiRequest request,
    ) async {
      return jsonResponse(
        401,
        jsonEncode(<String, Object?>{
          'code': 'authentication_failed',
          'detail': 'private framework traceback and account lookup detail',
        }),
      );
    });
    final ApiClient client = _client(transport);

    await expectLater(
      AuthRepository(
        apiClient: client,
      ).login(email: 'reviewer@example.test', password: 'wrong'),
      throwsA(
        isA<AuthException>()
            .having(
              (AuthException e) => e.failure,
              'failure',
              AuthFailure.invalidCredentials,
            )
            .having(
              (AuthException e) => e.message,
              'message',
              'Email or password is incorrect.',
            ),
      ),
    );
    client.close();
  });

  test('malformed token responses fail as contract errors', () async {
    final ScriptedTransport transport = ScriptedTransport(
      (ApiRequest request) async =>
          jsonResponse(200, jsonEncode(<String, Object?>{'access': 'x'})),
    );
    final ApiClient client = _client(transport);

    await expectLater(
      AuthRepository(
        apiClient: client,
      ).login(email: 'a@example.test', password: 'secret'),
      throwsA(
        isA<AuthException>().having(
          (AuthException e) => e.failure,
          'failure',
          AuthFailure.contract,
        ),
      ),
    );
    client.close();
  });

  test('rate limiting is mapped without retrying the login request', () async {
    final ScriptedTransport transport = ScriptedTransport((
      ApiRequest request,
    ) async {
      return jsonResponse(
        429,
        jsonEncode(<String, Object?>{
          'code': 'rate_limited',
          'detail': 'Too many requests. Please try again later.',
        }),
      );
    });
    final ApiClient client = _client(transport);

    await expectLater(
      AuthRepository(
        apiClient: client,
      ).login(email: 'a@example.test', password: 'secret'),
      throwsA(
        isA<AuthException>().having(
          (AuthException e) => e.failure,
          'failure',
          AuthFailure.rateLimited,
        ),
      ),
    );
    expect(transport.requests, hasLength(1));
    client.close();
  });

  test(
    'decoding malformed profile JSON is rejected rather than trusted',
    () async {
      final ScriptedTransport transport = ScriptedTransport(
        (ApiRequest request) async => jsonResponse(200, 'not-json'),
      );
      final ApiClient client = _client(transport);

      await expectLater(
        AuthRepository(apiClient: client).currentUser('access-one'),
        throwsA(
          isA<AuthException>().having(
            (AuthException e) => e.failure,
            'failure',
            AuthFailure.contract,
          ),
        ),
      );
      client.close();
    },
  );
}

ApiClient _client(ScriptedTransport transport) => ApiClient(
  config: AppConfig.fromValues(
    apiBaseUrl: 'http://127.0.0.1:8000/api/v1/',
    environment: 'test',
  ),
  transport: transport,
);
