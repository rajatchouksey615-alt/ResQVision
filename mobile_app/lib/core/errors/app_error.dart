import 'dart:async';
import 'dart:io';

import 'app_exception.dart';

class AppError {
  const AppError({required this.kind, required this.message});

  final AppErrorKind kind;
  final String message;
}

abstract final class AppErrorMapper {
  static AppError fromException(Object error) {
    if (error is AppException) {
      return AppError(kind: error.kind, message: error.message);
    }
    if (error is TimeoutException) {
      return const AppError(
        kind: AppErrorKind.timeout,
        message: 'The server took too long to respond. Try again.',
      );
    }
    if (error is IOException) {
      return const AppError(
        kind: AppErrorKind.network,
        message:
            'The server could not be reached. Check the connection and try again.',
      );
    }
    return const AppError(
      kind: AppErrorKind.unexpected,
      message: 'Something went wrong. Please try again.',
    );
  }
}
