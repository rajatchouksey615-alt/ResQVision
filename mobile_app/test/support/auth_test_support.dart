import 'dart:convert';

import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/networking/api_transport.dart';
import 'package:resqvision_mobile/core/networking/authenticated_api_client.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/core/security/token_storage.dart';
import 'package:resqvision_mobile/features/authentication/application/auth_session_controller.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_repository.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';

class MemoryTokenStorage implements TokenStorage {
  AuthTokens? tokens;
  bool failReads = false;
  bool failWrites = false;
  bool failClears = false;
  final List<AuthTokens> writes = <AuthTokens>[];

  @override
  Future<AuthTokens?> readTokens() async {
    if (failReads) throw const TokenStorageException();
    return tokens;
  }

  @override
  Future<void> writeTokens(AuthTokens value) async {
    if (failWrites) throw const TokenStorageException();
    tokens = value;
    writes.add(value);
  }

  @override
  Future<void> clearTokens() async {
    if (failClears) throw const TokenStorageException();
    tokens = null;
  }
}

class ScriptedTransport implements ApiTransport {
  ScriptedTransport(this.respond);

  final Future<ApiResponse> Function(ApiRequest request) respond;
  final List<ApiRequest> requests = <ApiRequest>[];
  bool closed = false;

  @override
  Future<ApiResponse> send(
    ApiRequest request, {
    required Duration connectionTimeout,
    required Duration responseTimeout,
  }) {
    requests.add(request);
    return respond(request);
  }

  @override
  void close() => closed = true;
}

class AuthHarness {
  AuthHarness({required this.transport, MemoryTokenStorage? storage})
    : storage = storage ?? MemoryTokenStorage() {
    apiClient = ApiClient(
      config: AppConfig.fromValues(
        apiBaseUrl: 'http://127.0.0.1:8000/api/v1/',
        environment: 'test',
      ),
      transport: transport,
    );
    repository = AuthRepository(apiClient: apiClient);
    session = AuthSessionController(
      repository: repository,
      tokenStorage: this.storage,
    );
    authenticatedApiClient = AuthenticatedApiClient(
      apiClient: apiClient,
      session: session,
    );
    dashboardRepository = DashboardRepository(
      apiClient: authenticatedApiClient,
    );
  }

  final MemoryTokenStorage storage;
  final ScriptedTransport transport;
  late final ApiClient apiClient;
  late final AuthRepository repository;
  late final AuthSessionController session;
  late final AuthenticatedApiClient authenticatedApiClient;
  late final DashboardRepository dashboardRepository;

  void close() {
    session.dispose();
    apiClient.close();
  }
}

ApiResponse jsonResponse(int status, String body) =>
    ApiResponse(statusCode: status, body: body);

const Map<String, Object?> loginTokens = <String, Object?>{
  'access': 'access-one',
  'refresh': 'refresh-one',
};

const Map<String, Object?> rotatedTokens = <String, Object?>{
  'access': 'access-two',
  'refresh': 'refresh-two',
};

const Map<String, Object?> userProfile = <String, Object?>{
  'id': 'fbdc2770-2bcd-427b-9856-ef8e73d46752',
  'email': 'reviewer@example.test',
  'first_name': 'Rajat',
  'last_name': 'Reviewer',
  'roles': <String>['POLICE'],
  'memberships': <Object?>[
    <String, Object?>{
      'id': 'e751879f-4ab3-42f3-9d6d-8e867503b00d',
      'organization_id': '6b0eb8c2-9f06-4cac-83ed-56b7654b9f4c',
      'organization_code': 'central-police',
      'organization_name': 'Central Police',
      'organization_kind': 'POLICE',
      'role': 'POLICE',
      'status': 'ACTIVE',
      'created_at': '2026-11-17T10:00:00Z',
    },
  ],
};

ApiResponse tokenResponse(Map<String, Object?> tokens) =>
    jsonResponse(200, jsonEncode(tokens));

ApiResponse profileResponse() => jsonResponse(200, jsonEncode(userProfile));
