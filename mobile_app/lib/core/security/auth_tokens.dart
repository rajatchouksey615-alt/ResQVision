class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});

  final String access;
  final String refresh;

  factory AuthTokens.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Token response must be an object.');
    }
    final Object? accessValue = value['access'];
    final Object? refreshValue = value['refresh'];
    if (accessValue is! String ||
        accessValue.isEmpty ||
        refreshValue is! String ||
        refreshValue.isEmpty) {
      throw const FormatException('Token response is incomplete.');
    }
    return AuthTokens(access: accessValue, refresh: refreshValue);
  }
}
