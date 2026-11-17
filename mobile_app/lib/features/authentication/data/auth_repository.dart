import 'dart:convert';

import '../../../../core/errors/app_exception.dart';
import '../../../../core/networking/api_client.dart';
import '../../../../core/networking/api_request.dart';
import '../../../../core/security/auth_tokens.dart';
import 'auth_failure.dart';
import 'models/authenticated_user.dart';

class AuthRepository {
  AuthRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;

  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    final ApiResponse response = await _send(
      'POST',
      'auth/token/',
      jsonBody: <String, Object?>{
        'email': email.trim().toLowerCase(),
        'password': password,
      },
    );
    _expectStatus(response, const <int>{200}, request: 'login');
    try {
      return AuthTokens.fromJson(_decodeJson(response.body));
    } on FormatException {
      throw const AuthException(
        AuthFailure.contract,
        'The sign-in response could not be read. Please try again.',
      );
    }
  }

  Future<AuthTokens> refresh(String refreshToken) async {
    final ApiResponse response = await _send(
      'POST',
      'auth/token/refresh/',
      jsonBody: <String, Object?>{'refresh': refreshToken},
    );
    _expectStatus(response, const <int>{200}, request: 'refresh');
    try {
      return AuthTokens.fromJson(_decodeJson(response.body));
    } on FormatException {
      throw const AuthException(
        AuthFailure.contract,
        'The session response could not be read. Please sign in again.',
      );
    }
  }

  Future<AuthenticatedUser> currentUser(String accessToken) async {
    final ApiResponse response = await _send(
      'GET',
      'auth/me/',
      headers: <String, String>{'Authorization': 'Bearer $accessToken'},
    );
    _expectStatus(response, const <int>{200}, request: 'profile');
    try {
      return AuthenticatedUser.fromJson(_decodeJson(response.body));
    } on FormatException {
      throw const AuthException(
        AuthFailure.contract,
        'The account profile could not be read. Please try again.',
      );
    }
  }

  Future<void> logout({
    required String accessToken,
    required String refreshToken,
  }) async {
    final ApiResponse response = await _send(
      'POST',
      'auth/logout/',
      headers: <String, String>{'Authorization': 'Bearer $accessToken'},
      jsonBody: <String, Object?>{'refresh': refreshToken},
    );
    _expectStatus(response, const <int>{204}, request: 'logout');
  }

  Future<ApiResponse> _send(
    String method,
    String path, {
    Map<String, String> headers = const <String, String>{},
    Object? jsonBody,
  }) async {
    try {
      return await _apiClient.request(
        method,
        path,
        headers: headers,
        jsonBody: jsonBody,
      );
    } on AppException catch (error) {
      final AuthFailure failure = switch (error.kind) {
        AppErrorKind.network => AuthFailure.network,
        AppErrorKind.timeout => AuthFailure.timeout,
        _ => AuthFailure.unexpected,
      };
      throw AuthException(failure, error.message);
    }
  }

  Object? _decodeJson(String body) {
    try {
      return jsonDecode(body);
    } on FormatException {
      throw const FormatException('Response JSON is invalid.');
    }
  }

  void _expectStatus(
    ApiResponse response,
    Set<int> accepted, {
    required String request,
  }) {
    if (accepted.contains(response.statusCode)) return;
    final int status = response.statusCode;
    final AuthFailure failure;
    final String message;
    if (status == 401) {
      if (request == 'login') {
        failure = AuthFailure.invalidCredentials;
        message = 'Email or password is incorrect.';
      } else {
        failure = AuthFailure.invalidSession;
        message = 'Your session has expired. Please sign in again.';
      }
    } else if (status == 429) {
      failure = AuthFailure.rateLimited;
      message = 'Too many attempts. Wait a moment, then try again.';
    } else if (status == 403) {
      failure = AuthFailure.forbidden;
      message = 'This account cannot access ResQVision.';
    } else if (status == 400) {
      failure = AuthFailure.invalidCredentials;
      message = 'Check the information and try again.';
    } else if (status >= 500) {
      failure = AuthFailure.server;
      message = 'ResQVision is temporarily unavailable. Please try again.';
    } else {
      failure = AuthFailure.unexpected;
      message = 'The request could not be completed. Please try again.';
    }
    throw AuthException(failure, message, statusCode: status);
  }
}
