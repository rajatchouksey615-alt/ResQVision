import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/section_heading.dart';
import '../application/auth_session_controller.dart';
import '../data/models/authenticated_user.dart';

class RoleLandingScreen extends StatelessWidget {
  const RoleLandingScreen({
    super.key,
    required this.session,
    required this.user,
  });

  final AuthSessionController session;
  final AuthenticatedUser user;

  @override
  Widget build(BuildContext context) {
    final List<String> roles = user.availableRoles;
    final List<OrganizationMembership> memberships = user.memberships
        .where(
          (OrganizationMembership membership) =>
              membership.status == 'ACTIVE' && roles.contains(membership.role),
        )
        .toList(growable: false);

    return Scaffold(
      appBar: AppBar(
        title: const Text('ResQVision'),
        actions: <Widget>[
          TextButton.icon(
            onPressed: () => session.logout(),
            icon: const Icon(Icons.logout),
            label: const Text('Sign out'),
          ),
          const SizedBox(width: AppSpacing.sm),
        ],
      ),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width = constraints.maxWidth > 760
                ? 680
                : constraints.maxWidth;
            return SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: width),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      Text(
                        'Welcome, ${user.displayName}',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        user.email,
                        style: Theme.of(context).textTheme.bodyLarge,
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      if (roles.isEmpty)
                        AppCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              const SectionHeading(
                                title: 'Workspace unavailable',
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              const Text(
                                'Your account is signed in, but no supported workspace is assigned. Contact your organization administrator.',
                              ),
                            ],
                          ),
                        )
                      else ...<Widget>[
                        const SectionHeading(
                          title: 'Your workspaces',
                          description:
                              'These entry points use roles and memberships returned by ResQVision.',
                        ),
                        const SizedBox(height: AppSpacing.md),
                        for (final String role in roles)
                          Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.md,
                            ),
                            child: AppCard(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Row(
                                    children: <Widget>[
                                      Icon(_iconForRole(role), size: 28),
                                      const SizedBox(width: AppSpacing.md),
                                      Expanded(
                                        child: Text(
                                          '$role workspace',
                                          style: Theme.of(
                                            context,
                                          ).textTheme.titleLarge,
                                        ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: AppSpacing.md),
                                  Text(
                                    'The $role dashboard will be added in a later phase.',
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodyMedium,
                                  ),
                                  for (final OrganizationMembership membership
                                      in memberships.where(
                                        (OrganizationMembership item) =>
                                            item.role == role,
                                      )) ...<Widget>[
                                    const SizedBox(height: AppSpacing.sm),
                                    Text(
                                      '${membership.organizationName} · ${membership.organizationCode}',
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  IconData _iconForRole(String role) => switch (role) {
    'ADMIN' => Icons.admin_panel_settings_outlined,
    'POLICE' => Icons.local_police_outlined,
    'HOSPITAL' => Icons.local_hospital_outlined,
    _ => Icons.work_outline,
  };
}
