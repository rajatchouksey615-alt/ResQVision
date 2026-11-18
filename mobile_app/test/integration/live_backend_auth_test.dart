import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
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
  final bool roleDashboardAccountsConfigured = <String>[
    'RESQVISION_TEST_ADMIN_EMAIL',
    'RESQVISION_TEST_ADMIN_PASSWORD',
    'RESQVISION_TEST_POLICE_EMAIL',
    'RESQVISION_TEST_POLICE_PASSWORD',
    'RESQVISION_TEST_HOSPITAL_EMAIL',
    'RESQVISION_TEST_HOSPITAL_PASSWORD',
  ].any((String name) => (Platform.environment[name] ?? '').isNotEmpty);
  final bool credentialsConfigured =
      baseUrl.isNotEmpty && email.isNotEmpty && password.isNotEmpty;
  final bool configured =
      credentialsConfigured && !roleDashboardAccountsConfigured;

  test(
    'live Django login, profile, refresh rotation, session restore, and logout',
    () async {
      _expectLocalTestTarget(baseUrl);
      expect(
        _isReservedTestEmail(email),
        isTrue,
        reason: 'Live auth regression accepts dedicated .test accounts only.',
      );
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
        expect(
          session.user?.email.toLowerCase() == email.toLowerCase(),
          isTrue,
          reason:
              'The returned profile must match the configured test account (value redacted).',
        );

        final AuthenticatedApiClient authenticated = AuthenticatedApiClient(
          apiClient: api,
          session: session,
        );
        final profile = await authenticated.request('GET', 'auth/me/');
        expect(profile.statusCode, 200);

        final beforeRotation = storage.tokens!;
        // The backend contract issues five-minute access tokens. Wait for the
        // real token to expire so this exercises live 401 -> refresh -> safe
        // GET replay without changing backend token settings.
        await Future<void>.delayed(const Duration(minutes: 5, seconds: 5));
        final ApiResponse recoveredProfile = await authenticated.request(
          'GET',
          'auth/me/',
        );
        expect(recoveredProfile.statusCode, 200);
        expect(
          storage.tokens?.refresh != beforeRotation.refresh,
          isTrue,
          reason:
              'An expired access token must rotate the refresh token (values redacted).',
        );
        expect(
          storage.tokens?.access != beforeRotation.access,
          isTrue,
          reason: 'An expired access token must be replaced (values redacted).',
        );
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
        : roleDashboardAccountsConfigured
        ? 'Run the live authentication lifecycle separately from role dashboard accounts to stay within the backend login throttle.'
        : 'Set RESQVISION_TEST_API_BASE_URL, RESQVISION_TEST_EMAIL, and RESQVISION_TEST_PASSWORD to run against a live Django server.',
    timeout: const Timeout(Duration(minutes: 7)),
  );
}

void _expectLocalTestTarget(String value) {
  final Uri? uri = Uri.tryParse(value);
  expect(
    uri != null && _isLoopback(uri),
    isTrue,
    reason: 'Live auth regression is restricted to a local development API.',
  );
}

bool _isReservedTestEmail(String value) {
  final String normalized = value.trim().toLowerCase();
  final int at = normalized.lastIndexOf('@');
  return at > 0 && normalized.substring(at + 1).endsWith('.test');
}

bool _isLoopback(Uri uri) {
  if (!uri.hasScheme ||
      !uri.hasAuthority ||
      uri.userInfo.isNotEmpty ||
      (uri.scheme != 'http' && uri.scheme != 'https')) {
    return false;
  }
  final String host = uri.host.toLowerCase();
  if (host == 'localhost' ||
      host == '::1' ||
      host.endsWith('.localhost') ||
      host.endsWith('.test')) {
    return true;
  }
  final InternetAddress? address = InternetAddress.tryParse(host);
  if (address == null || address.type != InternetAddressType.IPv4) return false;
  final List<int> octets = address.rawAddress;
  return octets[0] == 10 ||
      octets[0] == 127 ||
      (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31) ||
      (octets[0] == 192 && octets[1] == 168);
}
