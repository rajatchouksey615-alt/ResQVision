import '../errors/app_exception.dart';

enum AppEnvironment { development, test, staging, production }

class AppConfig {
  const AppConfig._({required this.environment, required this.apiBaseUrl});

  factory AppConfig.fromEnvironment({
    String apiBaseUrl = const String.fromEnvironment('API_BASE_URL'),
    String environment = const String.fromEnvironment(
      'APP_ENV',
      defaultValue: 'development',
    ),
  }) {
    return AppConfig.fromValues(
      apiBaseUrl: apiBaseUrl,
      environment: environment,
    );
  }

  factory AppConfig.fromValues({
    required String apiBaseUrl,
    String environment = 'development',
  }) {
    final String normalizedEnvironment = environment.trim().toLowerCase();
    AppEnvironment? parsedEnvironment;
    for (final AppEnvironment candidate in AppEnvironment.values) {
      if (candidate.name == normalizedEnvironment) {
        parsedEnvironment = candidate;
        break;
      }
    }
    if (parsedEnvironment == null) {
      throw const AppException(
        kind: AppErrorKind.configuration,
        message: 'APP_ENV must be development, test, staging, or production.',
      );
    }

    final Uri parsedUrl = _parseApiBaseUrl(apiBaseUrl);
    if (parsedEnvironment == AppEnvironment.production &&
        parsedUrl.scheme != 'https') {
      throw const AppException(
        kind: AppErrorKind.configuration,
        message: 'Production API_BASE_URL values must use HTTPS.',
      );
    }

    final String path = parsedUrl.path.endsWith('/')
        ? parsedUrl.path
        : '${parsedUrl.path}/';
    return AppConfig._(
      environment: parsedEnvironment,
      apiBaseUrl: parsedUrl.replace(path: path),
    );
  }

  final AppEnvironment environment;
  final Uri apiBaseUrl;

  static Uri _parseApiBaseUrl(String value) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty) {
      throw const AppException(
        kind: AppErrorKind.configuration,
        message:
            'API_BASE_URL is missing. Start the app with --dart-define=API_BASE_URL=<base-url>; see mobile_app/README.md.',
      );
    }

    Uri? parsed;
    try {
      parsed = Uri.parse(trimmed);
    } on FormatException {
      parsed = null;
    }

    if (parsed == null ||
        !parsed.hasAuthority ||
        parsed.host.isEmpty ||
        (parsed.scheme != 'http' && parsed.scheme != 'https') ||
        parsed.userInfo.isNotEmpty ||
        parsed.hasQuery ||
        parsed.hasFragment ||
        (parsed.hasPort && (parsed.port < 1 || parsed.port > 65535))) {
      throw const AppException(
        kind: AppErrorKind.configuration,
        message:
            'API_BASE_URL must be an absolute HTTP or HTTPS URL without credentials, query, or fragment.',
      );
    }
    return parsed;
  }
}
