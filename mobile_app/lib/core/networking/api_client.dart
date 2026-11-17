import 'dart:async';
import 'dart:io';

import '../config/app_config.dart';
import '../errors/app_exception.dart';
import 'api_request.dart';
import 'api_transport.dart';

class ApiClient {
  ApiClient({
    required AppConfig config,
    ApiTransport? transport,
    this.connectionTimeout = const Duration(seconds: 8),
    this.responseTimeout = const Duration(seconds: 12),
  }) : _baseUrl = config.apiBaseUrl,
       _transport = transport ?? IoApiTransport();

  final Uri _baseUrl;
  final ApiTransport _transport;
  final Duration connectionTimeout;
  final Duration responseTimeout;

  Future<ApiResponse> request(
    String method,
    String path, {
    Map<String, String> headers = const <String, String>{},
    Object? jsonBody,
  }) async {
    final String normalizedMethod = method.trim().toUpperCase();
    if (normalizedMethod.isEmpty) {
      throw ArgumentError.value(method, 'method', 'HTTP method is required.');
    }
    final Uri uri = _resolvePath(path);
    final ApiRequest request = ApiRequest(
      method: normalizedMethod,
      uri: uri,
      headers: headers,
      jsonBody: jsonBody,
    );

    try {
      return await _transport.send(
        request,
        connectionTimeout: connectionTimeout,
        responseTimeout: responseTimeout,
      );
    } on TimeoutException catch (error) {
      throw AppException(
        kind: AppErrorKind.timeout,
        message: 'The server took too long to respond. Try again.',
        causeType: error.runtimeType.toString(),
      );
    } on IOException catch (error) {
      throw AppException(
        kind: AppErrorKind.network,
        message:
            'The server could not be reached. Check the connection and try again.',
        causeType: error.runtimeType.toString(),
      );
    }
  }

  Uri _resolvePath(String path) {
    final String normalizedPath = path.trim().replaceFirst(RegExp(r'^/+'), '');
    if (normalizedPath.isEmpty ||
        normalizedPath.startsWith('../') ||
        normalizedPath == '..') {
      throw ArgumentError.value(
        path,
        'path',
        'A relative API path is required.',
      );
    }
    final Uri parsedPath = Uri.parse(normalizedPath);
    if (parsedPath.hasScheme || parsedPath.hasAuthority) {
      throw ArgumentError.value(
        path,
        'path',
        'Provide an API-relative path, not an absolute URL.',
      );
    }
    return _baseUrl.resolveUri(parsedPath);
  }

  void close() => _transport.close();
}
