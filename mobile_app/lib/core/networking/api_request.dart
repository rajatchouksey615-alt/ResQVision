class ApiRequest {
  ApiRequest({
    required this.method,
    required this.uri,
    Map<String, String> headers = const <String, String>{},
    this.jsonBody,
  }) : headers = Map<String, String>.unmodifiable(headers);

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final Object? jsonBody;
}

class ApiResponse {
  ApiResponse({
    required this.statusCode,
    required this.body,
    Map<String, List<String>> headers = const <String, List<String>>{},
  }) : headers = Map<String, List<String>>.unmodifiable(
         headers.map(
           (String key, List<String> value) => MapEntry<String, List<String>>(
             key,
             List<String>.unmodifiable(value),
           ),
         ),
       );

  final int statusCode;
  final String body;
  final Map<String, List<String>> headers;
}
