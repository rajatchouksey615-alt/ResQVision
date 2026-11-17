enum AuthFailure {
  invalidCredentials,
  invalidSession,
  rateLimited,
  forbidden,
  server,
  network,
  timeout,
  contract,
  storage,
  unexpected,
}

class AuthException implements Exception {
  const AuthException(this.failure, this.message, {this.statusCode});

  final AuthFailure failure;
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}
