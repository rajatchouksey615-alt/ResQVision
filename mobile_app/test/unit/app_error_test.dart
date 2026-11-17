import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/errors/app_error.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';

void main() {
  group('AppErrorMapper', () {
    test('maps timeouts without exposing exception details', () {
      final AppError error = AppErrorMapper.fromException(
        TimeoutException('private request detail'),
      );

      expect(error.kind, AppErrorKind.timeout);
      expect(error.message, contains('too long'));
      expect(error.message, isNot(contains('private')));
    });

    test('maps transport failures to a stable network message', () {
      final AppError error = AppErrorMapper.fromException(
        const SocketException('private host and port'),
      );

      expect(error.kind, AppErrorKind.network);
      expect(error.message, contains('could not be reached'));
      expect(error.message, isNot(contains('private')));
    });

    test('maps unknown exceptions to a generic message', () {
      final AppError error = AppErrorMapper.fromException(
        StateError('sensitive detail'),
      );

      expect(error.kind, AppErrorKind.unexpected);
      expect(error.message, isNot(contains('sensitive')));
    });
  });
}
