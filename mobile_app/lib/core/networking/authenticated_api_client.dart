import 'api_client.dart';
import 'api_request.dart';
import '../../features/authentication/application/auth_session_controller.dart';

class AuthenticatedApiClient {
  AuthenticatedApiClient({
    required ApiClient apiClient,
    required AuthSessionController session,
  }) : _apiClient = apiClient,
       _session = session;

  final ApiClient _apiClient;
  final AuthSessionController _session;

  Future<ApiResponse> request(
    String method,
    String path, {
    Map<String, String> headers = const <String, String>{},
    Object? jsonBody,
  }) async {
    final String normalizedMethod = method.trim().toUpperCase();
    if (_isPublicAuthenticationEndpoint(path)) {
      return _apiClient.request(
        normalizedMethod,
        path,
        headers: <String, String>{
          for (final MapEntry<String, String> header in headers.entries)
            if (header.key.toLowerCase() != 'authorization')
              header.key: header.value,
        },
        jsonBody: jsonBody,
      );
    }
    final int version = _session.sessionVersion;
    final String accessToken = _session.authenticatedAccessToken(version);
    final ApiResponse response = await _send(
      normalizedMethod,
      path,
      accessToken,
      headers,
      jsonBody,
    );
    if (response.statusCode != 401 || _isAuthenticationEndpoint(path)) {
      return response;
    }

    final String replacement = await _session.refreshAfterUnauthorized(
      rejectedAccessToken: accessToken,
      expectedVersion: version,
    );
    if (!_canReplay(normalizedMethod)) return response;
    if (_session.sessionVersion != version) return response;

    // Safe reads are replayed at most once; the request body and headers are retained.
    return _send(normalizedMethod, path, replacement, headers, jsonBody);
  }

  Future<ApiResponse> _send(
    String method,
    String path,
    String accessToken,
    Map<String, String> headers,
    Object? jsonBody,
  ) => _apiClient.request(
    method,
    path,
    headers: <String, String>{
      for (final MapEntry<String, String> header in headers.entries)
        if (header.key.toLowerCase() != 'authorization')
          header.key: header.value,
      'Authorization': 'Bearer $accessToken',
    },
    jsonBody: jsonBody,
  );

  bool _isAuthenticationEndpoint(String path) {
    final String normalized = path.trim().replaceFirst(RegExp(r'^/+'), '');
    return normalized.startsWith('auth/token/') ||
        normalized.startsWith('auth/logout/');
  }

  bool _isPublicAuthenticationEndpoint(String path) {
    final String normalized = path.trim().replaceFirst(RegExp(r'^/+'), '');
    return normalized.startsWith('auth/token/');
  }

  bool _canReplay(String method) =>
      method == 'GET' || method == 'HEAD' || method == 'OPTIONS';
}
