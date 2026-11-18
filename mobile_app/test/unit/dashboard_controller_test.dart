import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';
import 'package:resqvision_mobile/core/security/auth_tokens.dart';
import 'package:resqvision_mobile/features/dashboard/application/dashboard_controller.dart';
import 'package:resqvision_mobile/features/dashboard/data/dashboard_repository.dart';

import '../support/auth_test_support.dart';
import '../support/dashboard_test_support.dart';

void main() {
  test(
    'a stale role response cannot replace the newly selected workspace',
    () async {
      final Completer<ApiResponse> firstIncidentResponse =
          Completer<ApiResponse>();
      int incidentRequests = 0;
      final Map<String, Object?> profile = dashboardProfile(
        roles: const <String>['POLICE', 'HOSPITAL'],
        memberships: <Map<String, Object?>>[
          policeMembership(),
          hospitalMembership(),
        ],
      );
      final AuthHarness harness = AuthHarness(
        transport: ScriptedTransport((ApiRequest request) async {
          if (request.uri.path.endsWith('/auth/me/')) {
            return jsonApiResponse(200, profile);
          }
          if (request.uri.path.endsWith('/incidents/')) {
            incidentRequests++;
            if (incidentRequests == 1) return firstIncidentResponse.future;
            return pageResponse(results: <Map<String, Object?>>[incident()]);
          }
          if (request.uri.path.endsWith('/assignments/')) {
            return pageResponse(
              results: <Map<String, Object?>>[
                assignment(
                  organizationId: policeOrganizationId,
                  organizationKind: 'POLICE',
                ),
                assignment(
                  id: hospitalAssignmentId,
                  organizationId: hospitalOrganizationId,
                  organizationKind: 'HOSPITAL',
                ),
              ],
            );
          }
          throw StateError('Unexpected request path.');
        }),
      );
      harness.storage.tokens = AuthTokens.fromJson(loginTokens);
      await harness.session.restoreSession();
      final DashboardController controller = DashboardController(
        repository: harness.dashboardRepository,
        user: harness.session.user!,
        roles: const <DashboardRole>[
          DashboardRole.police,
          DashboardRole.hospital,
        ],
        initialRole: DashboardRole.police,
      );
      final Completer<void> hospitalDataLoaded = Completer<void>();
      controller.addListener(() {
        if (controller.selectedRole == DashboardRole.hospital &&
            controller.incidents.isNotEmpty &&
            !hospitalDataLoaded.isCompleted) {
          hospitalDataLoaded.complete();
        }
      });

      try {
        final Future<void> staleLoad = controller.refresh();
        controller.selectRole(DashboardRole.hospital);
        await hospitalDataLoaded.future.timeout(const Duration(seconds: 2));
        expect(
          controller.incidents.single.assignments.single.organizationKind,
          'HOSPITAL',
        );

        firstIncidentResponse.complete(
          pageResponse(results: <Map<String, Object?>>[incident()]),
        );
        await staleLoad;

        expect(controller.selectedRole, DashboardRole.hospital);
        expect(
          controller.incidents.single.assignments.single.organizationKind,
          'HOSPITAL',
        );
      } finally {
        controller.dispose();
        harness.close();
      }
    },
  );
}
