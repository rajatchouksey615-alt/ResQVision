import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';

void main() {
  group('AppConfig', () {
    test('requires an API base URL', () {
      expect(
        () => AppConfig.fromValues(apiBaseUrl: '  '),
        throwsA(
          isA<AppException>().having(
            (AppException error) => error.kind,
            'kind',
            AppErrorKind.configuration,
          ),
        ),
      );
    });

    test('accepts overrides and normalizes the base path', () {
      final AppConfig config = AppConfig.fromValues(
        apiBaseUrl: 'http://10.0.2.2:8000/api/v1',
        environment: 'development',
      );

      expect(config.environment, AppEnvironment.development);
      expect(config.apiBaseUrl.toString(), 'http://10.0.2.2:8000/api/v1/');
    });

    test('rejects malformed or unsafe API URLs', () {
      const List<String> invalidUrls = <String>[
        'localhost:8000',
        'ftp://api.example.test/v1/',
        'http://user:password@api.example.test/v1/',
        'http://api.example.test/v1/?token=secret',
        'http://api.example.test:70000/v1/',
      ];

      for (final String value in invalidUrls) {
        expect(
          () => AppConfig.fromValues(apiBaseUrl: value),
          throwsA(isA<AppException>()),
          reason: 'Expected $value to be rejected.',
        );
      }
    });

    test('requires HTTPS in production', () {
      expect(
        () => AppConfig.fromValues(
          apiBaseUrl: 'http://api.example.test/api/v1/',
          environment: 'production',
        ),
        throwsA(
          isA<AppException>().having(
            (AppException error) => error.kind,
            'kind',
            AppErrorKind.configuration,
          ),
        ),
      );
    });
  });
}
