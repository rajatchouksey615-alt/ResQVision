import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../dashboard/data/dashboard_repository.dart';
import '../../dashboard/presentation/dashboard_shell.dart';
import '../../incidents/data/incident_repository.dart';
import '../application/auth_session_controller.dart';
import '../data/models/authenticated_user.dart';

/// Routes an authenticated profile into the shared role-aware application shell.
class RoleLandingScreen extends StatelessWidget {
  const RoleLandingScreen({
    super.key,
    required this.session,
    required this.user,
    required this.dashboardRepository,
    this.incidentRepository,
  });

  final AuthSessionController session;
  final AuthenticatedUser user;
  final DashboardRepository? dashboardRepository;
  final IncidentRepository? incidentRepository;

  @override
  Widget build(BuildContext context) {
    final DashboardRepository? repository = dashboardRepository;
    if (repository == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('ResQVision')),
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(
                    'Dashboard data services are not configured for this app.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  TextButton.icon(
                    onPressed: () => session.logout(),
                    icon: const Icon(Icons.logout),
                    label: const Text('Sign out'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }
    return DashboardShell(
      session: session,
      user: user,
      repository: repository,
      incidentRepository: incidentRepository,
    );
  }
}
