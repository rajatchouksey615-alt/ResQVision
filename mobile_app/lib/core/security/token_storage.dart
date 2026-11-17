import 'auth_tokens.dart';

abstract interface class TokenStorage {
  Future<AuthTokens?> readTokens();

  Future<void> writeTokens(AuthTokens tokens);

  Future<void> clearTokens();
}

class TokenStorageException implements Exception {
  const TokenStorageException();
}
