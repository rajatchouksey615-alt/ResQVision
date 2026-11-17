import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_tokens.dart';
import 'token_storage.dart';

class FlutterTokenStorage implements TokenStorage {
  FlutterTokenStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const String _accessKey = 'resqvision.auth.access';
  static const String _refreshKey = 'resqvision.auth.refresh';

  final FlutterSecureStorage _storage;

  @override
  Future<AuthTokens?> readTokens() async {
    try {
      final List<String?> values = await Future.wait<String?>(<Future<String?>>[
        _storage.read(key: _accessKey),
        _storage.read(key: _refreshKey),
      ]);
      final String? access = values[0];
      final String? refresh = values[1];
      if ((access == null || access.isEmpty) &&
          (refresh == null || refresh.isEmpty)) {
        return null;
      }
      if (access == null ||
          access.isEmpty ||
          refresh == null ||
          refresh.isEmpty) {
        await clearTokens();
        return null;
      }
      return AuthTokens(access: access, refresh: refresh);
    } on TokenStorageException {
      rethrow;
    } catch (_) {
      throw const TokenStorageException();
    }
  }

  @override
  Future<void> writeTokens(AuthTokens tokens) async {
    try {
      // The refresh credential is replaced first because the server blacklists
      // its predecessor as soon as it rotates the pair.
      await _storage.write(key: _refreshKey, value: tokens.refresh);
      await _storage.write(key: _accessKey, value: tokens.access);
    } catch (_) {
      try {
        await clearTokens();
      } catch (_) {
        // The caller still receives an explicit failure; there is no plaintext fallback.
      }
      throw const TokenStorageException();
    }
  }

  @override
  Future<void> clearTokens() async {
    Object? failure;
    for (final String key in <String>[_accessKey, _refreshKey]) {
      try {
        await _storage.delete(key: key);
      } catch (error) {
        failure ??= error;
      }
    }
    if (failure != null) {
      throw const TokenStorageException();
    }
  }
}
