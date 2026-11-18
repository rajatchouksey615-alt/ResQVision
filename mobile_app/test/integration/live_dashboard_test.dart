import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_client.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/networking/api_transport.dart';
import 'package:resqvision_mobile/core/networking/authenticated_api_client.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/core/security/token_storage.dart';
import 'package:resqvision_mobile/features/authentication/application/auth_session_controller.dart';
import 'package:resqvision_mobile/features/authentication/data/auth_repository.dart';
import 'package:resqvision_mobile/features/authentication/data/models/authenticated_user.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';

void main() {
  final String baseUrl =
      Platform.environment['RESQVISION_TEST_API_BASE_URL'] ?? '';
  final _TestAccount generalAccount = _TestAccount.fromEnvironment(
    'RESQVISION_TEST_EMAIL',
    'RESQVISION_TEST_PASSWORD',
  );
  final Map<DashboardRole, _TestAccount> roleAccounts =
      <DashboardRole, _TestAccount>{
        DashboardRole.admin: _TestAccount.fromEnvironment(
          'RESQVISION_TEST_ADMIN_EMAIL',
          'RESQVISION_TEST_ADMIN_PASSWORD',
        ),
        DashboardRole.police: _TestAccount.fromEnvironment(
          'RESQVISION_TEST_POLICE_EMAIL',
          'RESQVISION_TEST_POLICE_PASSWORD',
        ),
        DashboardRole.hospital: _TestAccount.fromEnvironment(
          'RESQVISION_TEST_HOSPITAL_EMAIL',
          'RESQVISION_TEST_HOSPITAL_PASSWORD',
        ),
      };

  for (final DashboardRole role in DashboardRole.values) {
    final _TestAccount account = roleAccounts[role]!;
    test(
      'live ${role.title} dashboard reads only backend-authorized scope',
      () =>
          _verifyRoleDashboard(baseUrl: baseUrl, role: role, account: account),
      skip: account.isAbsent
          ? 'Set the dedicated RESQVISION_TEST_${role.code}_EMAIL and _PASSWORD for this role.'
          : null,
    );
  }

  final bool anyRoleAccountConfigured = roleAccounts.values.any(
    (_TestAccount account) => !account.isAbsent,
  );
  test(
    'live configured account checks each role and membership returned by Django',
    () => _verifyAllAccountScopes(baseUrl: baseUrl, account: generalAccount),
    skip: generalAccount.isAbsent || anyRoleAccountConfigured
        ? 'Set the three generic RESQVISION_TEST_* values and omit role-specific accounts to run the single-account scope check.'
        : null,
  );

  test(
    'live unauthenticated incident reads are rejected',
    () async {
      _expectLocalTestTarget(baseUrl);
      final ApiClient api = _newApiClient(baseUrl);
      try {
        final ApiResponse response = await api.request(
          'GET',
          'incidents/?limit=1&offset=0',
        );
        expect(response.statusCode, 401);
      } finally {
        api.close();
      }
    },
    skip: baseUrl.isEmpty ? 'Set RESQVISION_TEST_API_BASE_URL.' : null,
  );

  final _TestAccount policeAccount = roleAccounts[DashboardRole.police]!;
  final _TestAccount hospitalAccount = roleAccounts[DashboardRole.hospital]!;
  test(
    'live Police and Hospital scopes and refresh-token ownership stay isolated',
    () => _verifyCrossAccountAuthorization(
      baseUrl: baseUrl,
      policeAccount: policeAccount,
      hospitalAccount: hospitalAccount,
    ),
    skip: policeAccount.isAbsent || hospitalAccount.isAbsent
        ? 'Configure dedicated Police and Hospital .test accounts to verify live organization isolation and the 403 boundary.'
        : null,
  );
}

Future<void> _verifyRoleDashboard({
  required String baseUrl,
  required DashboardRole role,
  required _TestAccount account,
}) async {
  _expectLocalTestTarget(baseUrl);
  _expectCompleteTestAccount(account);

  final _RecordingTransport transport = _RecordingTransport();
  final ApiClient api = _newApiClient(baseUrl, transport: transport);
  final _MemoryTokenStorage storage = _MemoryTokenStorage();
  final AuthSessionController session = _newSession(api, storage);
  final AuthenticatedApiClient authenticated = AuthenticatedApiClient(
    apiClient: api,
    session: session,
  );
  final DashboardRepository dashboard = DashboardRepository(
    apiClient: authenticated,
  );

  try {
    await session.login(email: account.email, password: account.password);
    expect(
      session.status,
      SessionStatus.authenticated,
      reason:
          'The configured local test account must authenticate (values redacted).',
    );
    final AuthenticatedUser user = session.user!;
    expect(
      user.availableRoles,
      contains(role.code),
      reason: 'The dedicated account must receive ${role.code} from Django.',
    );
    if (role != DashboardRole.admin) {
      expect(
        _activeMembershipsForRole(user.memberships, role),
        isNotEmpty,
        reason:
            'The dedicated account must have an active ${role.code} membership.',
      );
    }

    final int firstCall = transport.calls.length;
    final DashboardPage page = await dashboard.loadPage(
      role: role,
      activeMemberships: user.memberships,
      organizationId: null,
    );
    if (role != DashboardRole.admin) {
      expect(page.incidents, hasLength(DashboardRepository.pageSize));
      expect(
        page.hasMore,
        isTrue,
        reason:
            'Six fixture incidents must produce a backend continuation link.',
      );
      expect(page.nextOffset, DashboardRepository.pageSize);
    } else if (_activeOperationalMemberships(user.memberships).isEmpty) {
      expect(
        page.incidents,
        isEmpty,
        reason:
            'Admin without organization membership must not gain global incident access.',
      );
    }
    _verifyPageAgainstBackendResponses(
      role: role,
      user: user,
      page: page,
      calls: transport.calls.skip(firstCall).toList(growable: false),
    );
    final LogoutResult logout = await session.logout();
    expect(logout.localCredentialsCleared, isTrue);
    expect(logout.serverRevocationConfirmed, isTrue);
  } finally {
    if (session.isAuthenticated) await session.logout();
    session.dispose();
    api.close();
  }
}

Future<void> _verifyAllAccountScopes({
  required String baseUrl,
  required _TestAccount account,
}) async {
  _expectLocalTestTarget(baseUrl);
  _expectCompleteTestAccount(account);

  final _RecordingTransport transport = _RecordingTransport();
  final ApiClient api = _newApiClient(baseUrl, transport: transport);
  final _MemoryTokenStorage storage = _MemoryTokenStorage();
  final AuthSessionController session = _newSession(api, storage);
  final DashboardRepository dashboard = DashboardRepository(
    apiClient: AuthenticatedApiClient(apiClient: api, session: session),
  );

  try {
    await session.login(email: account.email, password: account.password);
    expect(
      session.status,
      SessionStatus.authenticated,
      reason:
          'The configured local test account must authenticate (values redacted).',
    );
    final AuthenticatedUser user = session.user!;
    final List<DashboardRole> roles = user.availableRoles
        .map(DashboardRole.fromCode)
        .whereType<DashboardRole>()
        .toList(growable: false);
    expect(
      roles,
      isNotEmpty,
      reason: 'Django must return a supported human role.',
    );

    for (final DashboardRole role in roles) {
      final List<OrganizationMembership> activeRoleMemberships =
          _activeMembershipsForRole(user.memberships, role);
      if (role != DashboardRole.admin && activeRoleMemberships.isEmpty) {
        final int callCount = transport.calls.length;
        await expectLater(
          dashboard.loadPage(
            role: role,
            activeMemberships: user.memberships,
            organizationId: null,
          ),
          throwsA(isA<DashboardDataException>()),
        );
        expect(
          transport.calls.length,
          callCount,
          reason:
              'A role without active membership must not call dashboard APIs.',
        );
        continue;
      }

      final int firstCall = transport.calls.length;
      final DashboardPage page = await dashboard.loadPage(
        role: role,
        activeMemberships: user.memberships,
        organizationId: null,
      );
      _verifyPageAgainstBackendResponses(
        role: role,
        user: user,
        page: page,
        calls: transport.calls.skip(firstCall).toList(growable: false),
      );
    }
  } finally {
    if (session.isAuthenticated) await session.logout();
    session.dispose();
    api.close();
  }
}

void _verifyPageAgainstBackendResponses({
  required DashboardRole role,
  required AuthenticatedUser user,
  required DashboardPage page,
  required List<_RecordedCall> calls,
}) {
  final List<_RecordedCall> incidentCalls = calls
      .where((call) => call.request.uri.path.endsWith('/incidents/'))
      .toList(growable: false);
  expect(incidentCalls, hasLength(1));
  final _RecordedCall incidentCall = incidentCalls.single;
  expect(incidentCall.request.method, 'GET');
  expect(incidentCall.request.uri.queryParameters['limit'], '5');
  expect(incidentCall.request.uri.queryParameters['offset'], '0');
  expect(incidentCall.response.statusCode, 200);

  final Map<String, Object?> incidentPayload = _decodeObject(
    incidentCall.response.body,
  );
  final List<Object?> incidentRows = _results(incidentPayload);
  expect(incidentRows.length, lessThanOrEqualTo(5));
  expect(incidentPayload['count'], isA<int>());
  expect(page.totalCount, incidentPayload['count']);
  if (role == DashboardRole.admin &&
      _activeOperationalMemberships(user.memberships).isEmpty) {
    expect(
      incidentRows,
      isEmpty,
      reason:
          'Django must not return global incidents to an Admin without an active organization membership.',
    );
  }
  final String? incidentNext = _nullableString(incidentPayload, 'next');
  expect(page.hasMore, incidentNext != null);
  if (incidentNext != null) {
    final int? offset =
        Uri.tryParse(incidentNext)?.queryParameters['offset'] == null
        ? null
        : int.tryParse(Uri.parse(incidentNext).queryParameters['offset']!);
    expect(offset, isNotNull);
    expect(page.nextOffset, offset);
  } else {
    expect(
      page.nextOffset,
      int.parse(incidentCall.request.uri.queryParameters['offset']!),
    );
  }

  // The backend count describes the account's authorized incident scope. The
  // dashboard shows a five-row paginated preview and never labels that count as
  // a global or role-specific total.
  final Set<String> backendIncidentIds = incidentRows
      .map(
        (Object? row) => _requiredString(_decodeObject(jsonEncode(row)), 'id'),
      )
      .toSet();
  expect(
    page.incidents.every(
      (incident) => backendIncidentIds.contains(incident.id),
    ),
    isTrue,
  );

  final Map<String, OrganizationMembership> activeMembershipsById =
      <String, OrganizationMembership>{
        for (final OrganizationMembership membership in user.memberships)
          if (membership.status == 'ACTIVE' &&
              membership.role == membership.organizationKind &&
              (membership.organizationKind == 'POLICE' ||
                  membership.organizationKind == 'HOSPITAL'))
            membership.organizationId: membership,
      };
  final List<_RecordedCall> assignmentCalls = calls
      .where((call) => call.request.uri.path.endsWith('/assignments/'))
      .toList(growable: false);
  bool assignmentPaginationContinues = false;
  for (final _RecordedCall assignmentCall in assignmentCalls) {
    expect(assignmentCall.request.method, 'GET');
    expect(assignmentCall.request.uri.queryParameters['limit'], '100');
    expect(assignmentCall.request.uri.queryParameters['offset'], '0');
    expect(assignmentCall.response.statusCode, 200);
    final Map<String, Object?> payload = _decodeObject(
      assignmentCall.response.body,
    );
    final List<Object?> rows = _results(payload);
    expect(rows.length, lessThanOrEqualTo(100));
    assignmentPaginationContinues =
        assignmentPaginationContinues ||
        _nullableString(payload, 'next') != null;
    for (final Object? rawRow in rows) {
      final Map<String, Object?> assignment = _decodeObject(jsonEncode(rawRow));
      final String organizationId = _requiredString(
        assignment,
        'target_organization_id',
      );
      final String kind = _requiredString(
        assignment,
        'target_organization_kind',
      );
      expect(
        activeMembershipsById[organizationId]?.organizationKind,
        kind,
        reason:
            'Backend assignments must remain within active profile memberships.',
      );
    }
  }
  if (assignmentPaginationContinues) {
    expect(
      page.isPartial,
      isTrue,
      reason:
          'A backend next link beyond limit=100 must mark the dashboard data partial.',
    );
  }

  final Set<String> roleOrganizationIds = _activeMembershipsForRole(
    user.memberships,
    role,
  ).map((membership) => membership.organizationId).toSet();
  for (final incident in page.incidents) {
    expect(backendIncidentIds.contains(incident.id), isTrue);
    for (final assignment in incident.assignments) {
      expect(roleOrganizationIds.contains(assignment.organizationId), isTrue);
      if (role != DashboardRole.admin) {
        expect(assignment.organizationKind, role.code);
      }
    }
  }
}

Future<void> _verifyCrossAccountAuthorization({
  required String baseUrl,
  required _TestAccount policeAccount,
  required _TestAccount hospitalAccount,
}) async {
  _expectLocalTestTarget(baseUrl);
  _expectCompleteTestAccount(policeAccount);
  _expectCompleteTestAccount(hospitalAccount);
  expect(
    policeAccount.email.toLowerCase() != hospitalAccount.email.toLowerCase(),
    isTrue,
    reason: 'Police and Hospital checks require distinct test identities.',
  );

  final _RecordingTransport transport = _RecordingTransport();
  final ApiClient api = _newApiClient(baseUrl, transport: transport);
  final _MemoryTokenStorage policeStorage = _MemoryTokenStorage();
  final _MemoryTokenStorage hospitalStorage = _MemoryTokenStorage();
  final AuthSessionController policeSession = _newSession(api, policeStorage);
  final AuthSessionController hospitalSession = _newSession(
    api,
    hospitalStorage,
  );
  final AuthenticatedApiClient policeClient = AuthenticatedApiClient(
    apiClient: api,
    session: policeSession,
  );
  final AuthenticatedApiClient hospitalClient = AuthenticatedApiClient(
    apiClient: api,
    session: hospitalSession,
  );
  final DashboardRepository policeDashboard = DashboardRepository(
    apiClient: policeClient,
  );
  final DashboardRepository hospitalDashboard = DashboardRepository(
    apiClient: hospitalClient,
  );
  AuthSessionController? restoredHospitalSession;

  try {
    await policeSession.login(
      email: policeAccount.email,
      password: policeAccount.password,
    );
    await hospitalSession.login(
      email: hospitalAccount.email,
      password: hospitalAccount.password,
    );
    expect(policeSession.status, SessionStatus.authenticated);
    expect(hospitalSession.status, SessionStatus.authenticated);
    expect(policeSession.user!.availableRoles, contains('POLICE'));
    expect(hospitalSession.user!.availableRoles, contains('HOSPITAL'));
    expect(
      _activeMembershipsForRole(
        policeSession.user!.memberships,
        DashboardRole.police,
      ),
      isNotEmpty,
    );
    expect(
      _activeMembershipsForRole(
        hospitalSession.user!.memberships,
        DashboardRole.hospital,
      ),
      isNotEmpty,
    );

    final int policeFirstCall = transport.calls.length;
    final DashboardPage policePage = await policeDashboard.loadPage(
      role: DashboardRole.police,
      activeMemberships: policeSession.user!.memberships,
      organizationId: null,
    );
    _verifyPageAgainstBackendResponses(
      role: DashboardRole.police,
      user: policeSession.user!,
      page: policePage,
      calls: transport.calls.skip(policeFirstCall).toList(growable: false),
    );

    final int hospitalFirstCall = transport.calls.length;
    final DashboardPage hospitalPage = await hospitalDashboard.loadPage(
      role: DashboardRole.hospital,
      activeMemberships: hospitalSession.user!.memberships,
      organizationId: null,
    );
    _verifyPageAgainstBackendResponses(
      role: DashboardRole.hospital,
      user: hospitalSession.user!,
      page: hospitalPage,
      calls: transport.calls.skip(hospitalFirstCall).toList(growable: false),
    );

    final List<String> policeAssignmentIds = policePage.incidents
        .expand((incident) => incident.assignments)
        .map((assignment) => assignment.id)
        .toList(growable: false);
    final List<String> hospitalAssignmentIds = hospitalPage.incidents
        .expand((incident) => incident.assignments)
        .map((assignment) => assignment.id)
        .toList(growable: false);
    expect(policeAssignmentIds, isNotEmpty);
    expect(hospitalAssignmentIds, isNotEmpty);
    expect(
      policePage.incidents
          .expand((incident) => incident.assignments)
          .every((assignment) => assignment.organizationKind == 'POLICE'),
      isTrue,
    );
    expect(
      hospitalPage.incidents
          .expand((incident) => incident.assignments)
          .every((assignment) => assignment.organizationKind == 'HOSPITAL'),
      isTrue,
    );

    final ApiResponse policeReadingHospital = await policeClient.request(
      'GET',
      'assignments/${hospitalAssignmentIds.first}/',
    );
    expect(policeReadingHospital.statusCode, 404);
    final ApiResponse hospitalReadingPolice = await hospitalClient.request(
      'GET',
      'assignments/${policeAssignmentIds.first}/',
    );
    expect(hospitalReadingPolice.statusCode, 404);

    final String policeAccess = policeStorage.tokens!.access;
    final String hospitalRefresh = hospitalStorage.tokens!.refresh;
    final ApiResponse forbidden = await api.request(
      'POST',
      'auth/logout/',
      headers: <String, String>{'Authorization': 'Bearer $policeAccess'},
      jsonBody: <String, Object?>{'refresh': hospitalRefresh},
    );
    expect(forbidden.statusCode, 403);
    expect((await policeClient.request('GET', 'auth/me/')).statusCode, 200);
    expect((await hospitalClient.request('GET', 'auth/me/')).statusCode, 200);

    final ApiResponse hospitalRefreshAfterForbidden = await api.request(
      'POST',
      'auth/token/refresh/',
      jsonBody: <String, Object?>{'refresh': hospitalRefresh},
    );
    expect(hospitalRefreshAfterForbidden.statusCode, 200);
    final Map<String, Object?> rotatedPayload = _decodeObject(
      hospitalRefreshAfterForbidden.body,
    );
    final _MemoryTokenStorage rotatedStorage = _MemoryTokenStorage()
      ..tokens = AuthTokens(
        access: _requiredString(rotatedPayload, 'access'),
        refresh: _requiredString(rotatedPayload, 'refresh'),
      );
    restoredHospitalSession = _newSession(api, rotatedStorage);
    await restoredHospitalSession.restoreSession();
    expect(restoredHospitalSession.status, SessionStatus.authenticated);
    expect(
      restoredHospitalSession.user?.id == hospitalSession.user?.id,
      isTrue,
    );

    final LogoutResult oldHospitalSessionLogout = await hospitalSession
        .logout();
    expect(oldHospitalSessionLogout.localCredentialsCleared, isTrue);
    final LogoutResult hospitalLogout = await restoredHospitalSession.logout();
    expect(hospitalLogout.localCredentialsCleared, isTrue);
    expect(hospitalLogout.serverRevocationConfirmed, isTrue);
    final LogoutResult policeLogout = await policeSession.logout();
    expect(policeLogout.localCredentialsCleared, isTrue);
    expect(policeLogout.serverRevocationConfirmed, isTrue);
  } finally {
    if (policeSession.isAuthenticated) await policeSession.logout();
    if (hospitalSession.isAuthenticated) await hospitalSession.logout();
    if (restoredHospitalSession?.isAuthenticated ?? false) {
      await restoredHospitalSession!.logout();
    }
    policeSession.dispose();
    hospitalSession.dispose();
    restoredHospitalSession?.dispose();
    api.close();
  }
}

List<OrganizationMembership> _activeMembershipsForRole(
  List<OrganizationMembership> memberships,
  DashboardRole role,
) => memberships
    .where(
      (membership) =>
          membership.status == 'ACTIVE' &&
          membership.role == role.code &&
          membership.organizationKind == role.code,
    )
    .toList(growable: false);

List<OrganizationMembership> _activeOperationalMemberships(
  List<OrganizationMembership> memberships,
) => memberships
    .where(
      (membership) =>
          membership.status == 'ACTIVE' &&
          membership.role == membership.organizationKind &&
          (membership.organizationKind == 'POLICE' ||
              membership.organizationKind == 'HOSPITAL'),
    )
    .toList(growable: false);

void _expectCompleteTestAccount(_TestAccount account) {
  expect(
    account.isComplete,
    isTrue,
    reason: 'Both test account variables must be set (values redacted).',
  );
  expect(
    _isReservedTestEmail(account.email),
    isTrue,
    reason: 'Live integration tests accept dedicated .test accounts only.',
  );
}

bool _isReservedTestEmail(String email) {
  final String normalized = email.trim().toLowerCase();
  final int at = normalized.lastIndexOf('@');
  return at > 0 && normalized.substring(at + 1).endsWith('.test');
}

void _expectLocalTestTarget(String baseUrl) {
  expect(
    _isLocalTestUrl(baseUrl),
    isTrue,
    reason:
        'Live integration tests are restricted to a local development API (value redacted).',
  );
}

bool _isLocalTestUrl(String value) {
  final Uri? uri = Uri.tryParse(value);
  if (uri == null ||
      !uri.hasScheme ||
      !uri.hasAuthority ||
      uri.userInfo.isNotEmpty ||
      (uri.scheme != 'http' && uri.scheme != 'https')) {
    return false;
  }
  final String host = uri.host.toLowerCase();
  if (host == 'localhost' ||
      host == '::1' ||
      host.endsWith('.localhost') ||
      host.endsWith('.test')) {
    return true;
  }
  final InternetAddress? address = InternetAddress.tryParse(host);
  if (address == null || address.type != InternetAddressType.IPv4) return false;
  final List<int> octets = address.rawAddress;
  return octets[0] == 10 ||
      octets[0] == 127 ||
      (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31) ||
      (octets[0] == 192 && octets[1] == 168);
}

ApiClient _newApiClient(String baseUrl, {ApiTransport? transport}) => ApiClient(
  config: AppConfig.fromValues(apiBaseUrl: baseUrl, environment: 'test'),
  transport: transport,
);

AuthSessionController _newSession(ApiClient api, _MemoryTokenStorage storage) =>
    AuthSessionController(
      repository: AuthRepository(apiClient: api),
      tokenStorage: storage,
    );

Map<String, Object?> _decodeObject(String body) {
  final Object? decoded = jsonDecode(body);
  expect(decoded, isA<Map<String, dynamic>>());
  return (decoded! as Map<String, dynamic>).cast<String, Object?>();
}

List<Object?> _results(Map<String, Object?> page) {
  final Object? results = page['results'];
  expect(results, isA<List<Object?>>());
  return results! as List<Object?>;
}

String? _nullableString(Map<String, Object?> value, String key) {
  final Object? field = value[key];
  expect(field, anyOf(isNull, isA<String>()));
  return field as String?;
}

String _requiredString(Map<String, Object?> value, String key) {
  final Object? field = value[key];
  expect(field, isA<String>());
  return field! as String;
}

class _TestAccount {
  const _TestAccount({required this.email, required this.password});

  factory _TestAccount.fromEnvironment(String emailName, String passwordName) =>
      _TestAccount(
        email: Platform.environment[emailName] ?? '',
        password: Platform.environment[passwordName] ?? '',
      );

  final String email;
  final String password;

  bool get isAbsent => email.isEmpty && password.isEmpty;
  bool get isComplete => email.isNotEmpty && password.isNotEmpty;
}

class _RecordedCall {
  const _RecordedCall({required this.request, required this.response});

  final ApiRequest request;
  final ApiResponse response;
}

class _RecordingTransport implements ApiTransport {
  _RecordingTransport({IoApiTransport? delegate})
    : _delegate = delegate ?? IoApiTransport();

  final IoApiTransport _delegate;
  final List<_RecordedCall> calls = <_RecordedCall>[];

  @override
  Future<ApiResponse> send(
    ApiRequest request, {
    required Duration connectionTimeout,
    required Duration responseTimeout,
  }) async {
    final ApiResponse response = await _delegate.send(
      request,
      connectionTimeout: connectionTimeout,
      responseTimeout: responseTimeout,
    );
    calls.add(_RecordedCall(request: request, response: response));
    return response;
  }

  @override
  void close() => _delegate.close();
}

class _MemoryTokenStorage implements TokenStorage {
  AuthTokens? tokens;

  @override
  Future<void> clearTokens() async => tokens = null;

  @override
  Future<AuthTokens?> readTokens() async => tokens;

  @override
  Future<void> writeTokens(AuthTokens value) async => tokens = value;
}
