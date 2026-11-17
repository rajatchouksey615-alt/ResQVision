import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/networking/api_transport.dart';

void main() {
  test('resolves API paths and prepares JSON requests centrally', () async {
    final _RecordingTransport transport = _RecordingTransport();
    final ApiClient client = ApiClient(
      config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
      transport: transport,
    );

    final ApiResponse response = await client.request(
      'post',
      '/prototype/checks',
      jsonBody: <String, Object?>{'note': 'sample'},
    );

    expect(response.statusCode, 204);
    expect(transport.lastRequest?.method, 'POST');
    expect(
      transport.lastRequest?.uri.toString(),
      'http://127.0.0.1:8000/api/v1/prototype/checks',
    );
    expect(transport.lastRequest?.jsonBody, <String, Object?>{
      'note': 'sample',
    });
    expect(
      transport.lastRequest?.headers.containsKey('Authorization'),
      isFalse,
    );
    expect(transport.connectionTimeout, const Duration(seconds: 8));
    expect(transport.responseTimeout, const Duration(seconds: 12));

    client.close();
    expect(transport.closed, isTrue);
  });

  test('maps transport timeouts without leaking their details', () async {
    final _RecordingTransport transport = _RecordingTransport(
      failure: TimeoutException('private server detail'),
    );
    final ApiClient client = ApiClient(
      config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
      transport: transport,
    );

    await expectLater(
      client.request('GET', 'status'),
      throwsA(
        isA<AppException>()
            .having(
              (AppException error) => error.kind,
              'kind',
              AppErrorKind.timeout,
            )
            .having(
              (AppException error) => error.message,
              'message',
              isNot(contains('private')),
            ),
      ),
    );
  });

  test('rejects absolute URLs as request paths', () async {
    final ApiClient client = ApiClient(
      config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
      transport: _RecordingTransport(),
    );

    await expectLater(
      client.request('GET', 'https://outside.example.test/data'),
      throwsArgumentError,
    );
  });
}

class _RecordingTransport implements ApiTransport {
  _RecordingTransport({this.failure});

  final Object? failure;
  ApiRequest? lastRequest;
  Duration? connectionTimeout;
  Duration? responseTimeout;
  bool closed = false;

  @override
  Future<ApiResponse> send(
    ApiRequest request, {
    required Duration connectionTimeout,
    required Duration responseTimeout,
  }) async {
    lastRequest = request;
    this.connectionTimeout = connectionTimeout;
    this.responseTimeout = responseTimeout;
    if (failure != null) {
      throw failure!;
    }
    return ApiResponse(statusCode: 204, body: '');
  }

  @override
  void close() => closed = true;
}
