import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/authenticated_api_client.dart';
import 'package:resqvision_mobile/features/authentication/application/auth_session_controller.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_failure.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_repository.dart';

import '../support/auth_test_support.dart';

void main() {
  final String baseUrl =
      Platform.environment['RESQVISION_TEST_API_BASE_URL'] ?? '';
  final String email = Platform.environment['RESQVISION_TEST_EMAIL'] ?? '';
  final String password =
      Platform.environment['RESQVISION_TEST_PASSWORD'] ?? '';
  final bool configured =
      baseUrl.isNotEmpty && email.isNotEmpty && password.isNotEmpty;

  test(
    'live Django login, profile, refresh rotation, session restore, and logout',
    () async {
      final ApiClient api = ApiClient(
        config: AppConfig.fromValues(apiBaseUrl: baseUrl, environment: 'test'),
      );
      final AuthRepository repository = AuthRepository(apiClient: api);
      final MemoryTokenStorage storage = MemoryTokenStorage();
      final AuthSessionController session = AuthSessionController(
        repository: repository,
        tokenStorage: storage,
      );
      AuthSessionController? restored;

      try {
        await expectLater(
          repository.login(email: email, password: '$password-invalid'),
          throwsA(
            isA<AuthException>().having(
              (AuthException error) => error.failure,
              'failure',
              AuthFailure.invalidCredentials,
            ),
          ),
        );

        await session.login(email: email, password: password);
        expect(
          session.status,
          SessionStatus.authenticated,
          reason: session.error?.message,
        );
        expect(session.user?.email, email.toLowerCase());

        final AuthenticatedApiClient authenticated = AuthenticatedApiClient(
          apiClient: api,
          session: session,
        );
        final profile = await authenticated.request('GET', 'auth/me/');
        expect(profile.statusCode, 200);

        final beforeRotation = storage.tokens!;
        final int version = session.sessionVersion;
        await session.refreshAfterUnauthorized(
          rejectedAccessToken: beforeRotation.access,
          expectedVersion: version,
        );
        expect(storage.tokens?.refresh, isNot(beforeRotation.refresh));
        expect(storage.tokens?.access, isNot(beforeRotation.access));
        await expectLater(
          repository.refresh(beforeRotation.refresh),
          throwsA(isA<AuthException>()),
        );

        restored = AuthSessionController(
          repository: repository,
          tokenStorage: storage,
        );
        await restored.restoreSession();
        expect(restored.status, SessionStatus.authenticated);
        expect(restored.user?.id, session.user?.id);

        final String finalRefresh = storage.tokens!.refresh;
        final logout = await restored.logout();
        expect(logout.localCredentialsCleared, isTrue);
        expect(logout.serverRevocationConfirmed, isTrue);
        expect(storage.tokens, isNull);
        await expectLater(
          repository.refresh(finalRefresh),
          throwsA(isA<AuthException>()),
        );
      } finally {
        restored?.dispose();
        session.dispose();
        api.close();
      }
    },
    skip: configured
        ? false
        : 'Set RESQVISION_TEST_API_BASE_URL, RESQVISION_TEST_EMAIL, and RESQVISION_TEST_PASSWORD to run against a live Django server.',
  );
}
