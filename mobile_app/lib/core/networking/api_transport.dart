import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'api_request.dart';

abstract interface class ApiTransport {
  Future<ApiResponse> send(
    ApiRequest request, {
    required Duration connectionTimeout,
    required Duration responseTimeout,
  });

  void close();
}

class IoApiTransport implements ApiTransport {
  IoApiTransport({HttpClient? client}) : _client = client ?? HttpClient();

  final HttpClient _client;

  @override
  Future<ApiResponse> send(
    ApiRequest request, {
    required Duration connectionTimeout,
    required Duration responseTimeout,
  }) async {
    _client.connectionTimeout = connectionTimeout;
    final HttpClientRequest outgoing = await _client
        .openUrl(request.method, request.uri)
        .timeout(connectionTimeout);
    outgoing.headers.set(HttpHeaders.acceptHeader, 'application/json');
    for (final MapEntry<String, String> header in request.headers.entries) {
      outgoing.headers.set(header.key, header.value);
    }
    if (request.jsonBody != null) {
      final List<int> body = utf8.encode(jsonEncode(request.jsonBody));
      outgoing.headers.contentType = ContentType.json;
      outgoing.contentLength = body.length;
      outgoing.add(body);
    }

    final HttpClientResponse incoming = await outgoing.close().timeout(
      responseTimeout,
    );
    final String responseBody = await incoming
        .transform(utf8.decoder)
        .join()
        .timeout(responseTimeout);
    final Map<String, List<String>> responseHeaders = <String, List<String>>{};
    incoming.headers.forEach((String name, List<String> values) {
      responseHeaders[name] = values;
    });

    return ApiResponse(
      statusCode: incoming.statusCode,
      body: responseBody,
      headers: responseHeaders,
    );
  }

  @override
  void close() => _client.close(force: true);
}
