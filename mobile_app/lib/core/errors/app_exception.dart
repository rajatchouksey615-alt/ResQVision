enum AppErrorKind { configuration, network, timeout, unexpected }

class AppException implements Exception {
  const AppException({
    required this.kind,
    required this.message,
    this.causeType,
  });

  final AppErrorKind kind;
  final String message;
  final String? causeType;

  @override
  String toString() => message;
}
