import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../../../core/security/auth_tokens.dart';
import '../../../../core/security/token_storage.dart';
import '../data/auth_failure.dart';
import '../data/auth_repository.dart';
import '../data/models/authenticated_user.dart';

enum SessionStatus {
  initializing,
  unauthenticated,
  authenticating,
  authenticated,
  refreshing,
  sessionExpired,
  recoverableError,
}

class LogoutResult {
  const LogoutResult({
    required this.localCredentialsCleared,
    required this.serverRevocationConfirmed,
  });

  final bool localCredentialsCleared;
  final bool serverRevocationConfirmed;
}

class AuthSessionController extends ChangeNotifier {
  AuthSessionController({
    required AuthRepository repository,
    required TokenStorage tokenStorage,
  }) : _repository = repository,
       _tokenStorage = tokenStorage;

  final AuthRepository _repository;
  final TokenStorage _tokenStorage;

  SessionStatus _status = SessionStatus.initializing;
  AuthenticatedUser? _user;
  AuthTokens? _tokens;
  AuthException? _error;
  String? _logoutNotice;
  int _generation = 0;
  Future<AuthTokens>? _refreshFuture;
  Future<void> _storageTail = Future<void>.value();

  SessionStatus get status => _status;
  AuthenticatedUser? get user => _user;
  AuthException? get error => _error;
  String? get logoutNotice => _logoutNotice;
  bool get isAuthenticated =>
      _user != null &&
      (_status == SessionStatus.authenticated ||
          _status == SessionStatus.refreshing);

  Future<void> restoreSession() async {
    final int generation = ++_generation;
    _user = null;
    _tokens = null;
    _error = null;
    _logoutNotice = null;
    _setStatus(SessionStatus.initializing);

    try {
      final AuthTokens? saved = await _serializeStorage<AuthTokens?>(
        _tokenStorage.readTokens,
      );
      if (generation != _generation) return;
      if (saved == null) {
        _setStatus(SessionStatus.unauthenticated);
        return;
      }
      _tokens = saved;
      final AuthenticatedUser profile = await _loadProfile(saved, generation);
      if (generation != _generation) return;
      _user = profile;
      _error = null;
      _setStatus(SessionStatus.authenticated);
    } on TokenStorageException {
      if (generation != _generation) return;
      _error = const AuthException(
        AuthFailure.storage,
        'Secure session storage is unavailable on this device.',
      );
      _setStatus(SessionStatus.recoverableError);
    } on AuthException catch (error) {
      if (generation != _generation) return;
      if (error.failure == AuthFailure.invalidSession) {
        await _expireSession(generation);
      } else {
        _error = error;
        _setStatus(SessionStatus.recoverableError);
      }
    } catch (_) {
      if (generation != _generation) return;
      _error = const AuthException(
        AuthFailure.unexpected,
        'The saved session could not be restored. Please try again.',
      );
      _setStatus(SessionStatus.recoverableError);
    }
  }

  Future<void> login({required String email, required String password}) async {
    final int generation = ++_generation;
    _error = null;
    _user = null;
    _tokens = null;
    _logoutNotice = null;
    _setStatus(SessionStatus.authenticating);
    try {
      final AuthTokens tokens = await _repository.login(
        email: email,
        password: password,
      );
      if (generation != _generation) return;
      await _saveTokens(tokens, generation);
      if (generation != _generation) return;
      _tokens = tokens;
      final AuthenticatedUser profile = await _repository.currentUser(
        tokens.access,
      );
      if (generation != _generation) return;
      _user = profile;
      _error = null;
      _setStatus(SessionStatus.authenticated);
    } on TokenStorageException {
      if (generation != _generation) return;
      _tokens = null;
      _user = null;
      try {
        await _clearStoredTokens();
      } on TokenStorageException {
        // Keep the session closed even when the platform store is unavailable.
      }
      _error = const AuthException(
        AuthFailure.storage,
        'Secure session storage is unavailable on this device. Sign-in was not saved.',
      );
      _setStatus(SessionStatus.unauthenticated);
    } on AuthException catch (error) {
      if (generation != _generation) return;
      if (error.failure == AuthFailure.invalidSession) {
        await _expireSession(generation);
      } else if (_tokens != null &&
          (error.failure == AuthFailure.network ||
              error.failure == AuthFailure.timeout ||
              error.failure == AuthFailure.server)) {
        _error = error;
        _setStatus(SessionStatus.recoverableError);
      } else {
        _tokens = null;
        _error = error;
        _setStatus(SessionStatus.unauthenticated);
      }
    } catch (_) {
      if (generation != _generation) return;
      _error = const AuthException(
        AuthFailure.unexpected,
        'Sign-in could not be completed. Please try again.',
      );
      _setStatus(SessionStatus.unauthenticated);
    }
  }

  void clearError() {
    if (_error == null) return;
    _error = null;
    notifyListeners();
  }

  Future<void> signInAgain() async {
    await logout();
  }

  Future<LogoutResult> logout() async {
    final AuthTokens? original = _tokens;
    final Future<AuthTokens>? refreshInFlight = _refreshFuture;
    ++_generation;
    _tokens = null;
    _user = null;
    _error = null;
    _logoutNotice = null;
    _setStatus(SessionStatus.unauthenticated);

    final Future<void> clearFuture = _clearStoredTokens();
    AuthTokens? latest = original;
    if (refreshInFlight != null) {
      try {
        latest = await refreshInFlight;
      } on AuthException {
        // Logout still proceeds with the best credential pair already held.
      }
    }

    bool localCleared = true;
    try {
      await clearFuture;
    } on TokenStorageException {
      localCleared = false;
    }

    bool serverRevocationConfirmed = latest == null;
    if (latest != null) {
      try {
        await _repository.logout(
          accessToken: latest.access,
          refreshToken: latest.refresh,
        );
        serverRevocationConfirmed = true;
      } on AuthException {
        serverRevocationConfirmed = false;
      }
    }

    if (!localCleared || !serverRevocationConfirmed) {
      _logoutNotice = !localCleared
          ? 'You are signed out in this app, but saved credentials could not be removed.'
          : 'You are signed out on this device. The server could not confirm session revocation.';
      notifyListeners();
    }
    return LogoutResult(
      localCredentialsCleared: localCleared,
      serverRevocationConfirmed: serverRevocationConfirmed,
    );
  }

  int get sessionVersion => _generation;

  String authenticatedAccessToken(int expectedVersion) {
    if (expectedVersion != _generation || !isAuthenticated || _tokens == null) {
      throw const AuthException(
        AuthFailure.invalidSession,
        'Your session has ended. Please sign in again.',
      );
    }
    return _tokens!.access;
  }

  Future<String> refreshAfterUnauthorized({
    required String rejectedAccessToken,
    required int expectedVersion,
  }) async {
    if (expectedVersion != _generation || _tokens == null) {
      throw const AuthException(
        AuthFailure.invalidSession,
        'Your session has ended. Please sign in again.',
      );
    }
    final AuthTokens current = _tokens!;
    if (current.access != rejectedAccessToken) return current.access;
    final AuthTokens replacement = await _refreshTokens(
      observedAccessToken: rejectedAccessToken,
      expectedGeneration: expectedVersion,
    );
    if (expectedVersion != _generation || _tokens == null) {
      throw const AuthException(
        AuthFailure.invalidSession,
        'Your session has ended. Please sign in again.',
      );
    }
    return replacement.access;
  }

  Future<AuthenticatedUser> _loadProfile(
    AuthTokens tokens,
    int generation,
  ) async {
    try {
      return await _repository.currentUser(tokens.access);
    } on AuthException catch (error) {
      if (error.failure != AuthFailure.invalidSession) rethrow;
      final AuthTokens rotated = await _refreshTokens(
        observedAccessToken: tokens.access,
        expectedGeneration: generation,
      );
      if (generation != _generation) {
        throw const AuthException(
          AuthFailure.invalidSession,
          'Your session has ended. Please sign in again.',
        );
      }
      return _repository.currentUser(rotated.access);
    }
  }

  Future<AuthTokens> _refreshTokens({
    required String observedAccessToken,
    required int expectedGeneration,
  }) {
    if (expectedGeneration != _generation || _tokens == null) {
      return Future<AuthTokens>.error(
        const AuthException(
          AuthFailure.invalidSession,
          'Your session has ended. Please sign in again.',
        ),
      );
    }
    final AuthTokens current = _tokens!;
    if (current.access != observedAccessToken) {
      return Future<AuthTokens>.value(current);
    }
    final Future<AuthTokens>? currentRefresh = _refreshFuture;
    if (currentRefresh != null) return currentRefresh;

    final Completer<AuthTokens> completer = Completer<AuthTokens>();
    final Future<AuthTokens> refreshFuture = completer.future;
    _refreshFuture = refreshFuture;
    final SessionStatus returnStatus = _status;
    _error = null;
    _setStatus(SessionStatus.refreshing);
    unawaited(
      _performRefresh(current, expectedGeneration, returnStatus)
          .then(
            completer.complete,
            onError: (Object error, StackTrace stackTrace) {
              completer.completeError(error, stackTrace);
            },
          )
          .whenComplete(() {
            if (identical(_refreshFuture, refreshFuture)) _refreshFuture = null;
          }),
    );
    return refreshFuture;
  }

  Future<AuthTokens> _performRefresh(
    AuthTokens current,
    int generation,
    SessionStatus returnStatus,
  ) async {
    try {
      final AuthTokens replacement = await _repository.refresh(current.refresh);
      if (generation != _generation) return replacement;
      await _saveTokens(replacement, generation);
      if (generation != _generation) return replacement;
      _tokens = replacement;
      _error = null;
      if (_user != null) {
        _setStatus(SessionStatus.authenticated);
      } else {
        _setStatus(
          returnStatus == SessionStatus.refreshing
              ? SessionStatus.initializing
              : returnStatus,
        );
      }
      return replacement;
    } on TokenStorageException {
      if (generation == _generation) {
        _tokens = null;
        _user = null;
        _error = const AuthException(
          AuthFailure.storage,
          'The refreshed session could not be saved securely.',
        );
        try {
          await _clearStoredTokens();
        } on TokenStorageException {
          // Keep the session unavailable even when cleanup fails.
        }
        _setStatus(SessionStatus.recoverableError);
      }
      throw const AuthException(
        AuthFailure.storage,
        'The refreshed session could not be saved securely.',
      );
    } on AuthException catch (error) {
      if (generation == _generation) {
        if (error.failure == AuthFailure.invalidSession) {
          await _expireSession(generation);
        } else if (_user == null) {
          _error = error;
          _setStatus(SessionStatus.recoverableError);
        } else {
          _error = error;
          _setStatus(SessionStatus.authenticated);
        }
      }
      rethrow;
    }
  }

  Future<void> _saveTokens(AuthTokens tokens, int generation) async {
    final bool saved = await _serializeStorage<bool>(() async {
      if (generation != _generation) return false;
      await _tokenStorage.writeTokens(tokens);
      return generation == _generation;
    });
    if (!saved) return;
  }

  Future<void> _expireSession(int generation) async {
    if (generation != _generation) return;
    ++_generation;
    _tokens = null;
    _user = null;
    _error = const AuthException(
      AuthFailure.invalidSession,
      'Your session has expired. Please sign in again.',
    );
    try {
      await _clearStoredTokens();
    } on TokenStorageException {
      // The expired session remains inaccessible in memory; the UI reports sign-in required.
    }
    _setStatus(SessionStatus.sessionExpired);
  }

  Future<void> _clearStoredTokens() =>
      _serializeStorage<void>(_tokenStorage.clearTokens);

  Future<T> _serializeStorage<T>(Future<T> Function() operation) {
    final Completer<T> result = Completer<T>();
    final Future<void> previous = _storageTail;
    _storageTail = () async {
      try {
        await previous;
      } catch (_) {
        // A failed operation does not prevent the next cleanup or write.
      }
      try {
        result.complete(await operation());
      } catch (error, stackTrace) {
        result.completeError(error, stackTrace);
      }
    }();
    return result.future;
  }

  void _setStatus(SessionStatus status) {
    _status = status;
    notifyListeners();
  }
}
