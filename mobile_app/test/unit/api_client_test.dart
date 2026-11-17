import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/networking/api_transport.dart';

void main() {
  test(
    'sends JSON with an explicit content length over the real HTTP transport',
    () async {
      final HttpServer server = await HttpServer.bind(
        InternetAddress.loopbackIPv4,
        0,
      );
      final Completer<Map<String, Object?>> received =
          Completer<Map<String, Object?>>();
      server.listen((HttpRequest request) async {
        final String body = await utf8.decoder.bind(request).join();
        if (!received.isCompleted) {
          received.complete(<String, Object?>{
            'transferEncoding': request.headers.value(
              HttpHeaders.transferEncodingHeader,
            ),
            'contentLength': request.contentLength,
            'body': body,
          });
        }
        request.response.statusCode = HttpStatus.noContent;
        await request.response.close();
      });
      final ApiClient client = ApiClient(
        config: AppConfig.fromValues(
          apiBaseUrl: 'http://127.0.0.1:${server.port}/api/v1/',
          environment: 'test',
        ),
      );

      try {
        final ApiResponse response = await client.request(
          'POST',
          'auth/token/',
          jsonBody: <String, Object?>{
            'email': 'reviewer@example.test',
            'password': 'secret',
          },
        );
        final Map<String, Object?> request = await received.future;
        final String expectedBody = jsonEncode(<String, Object?>{
          'email': 'reviewer@example.test',
          'password': 'secret',
        });

        expect(response.statusCode, HttpStatus.noContent);
        expect(request['transferEncoding'], isNull);
        expect(request['contentLength'], utf8.encode(expectedBody).length);
        expect(request['body'], expectedBody);
      } finally {
        client.close();
        await server.close(force: true);
      }
    },
  );

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
