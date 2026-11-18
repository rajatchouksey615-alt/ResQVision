import 'dart:async';

import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/section_heading.dart';
import '../../authentication/application/auth_session_controller.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../admin/admin_dashboard_screen.dart';
import '../application/dashboard_controller.dart';
import '../data/dashboard_repository.dart';
import '../hospital/hospital_dashboard_screen.dart';
import '../police/police_dashboard_screen.dart';
import 'dashboard_widgets.dart';

class DashboardShell extends StatefulWidget {
  const DashboardShell({
    super.key,
    required this.session,
    required this.user,
    required this.repository,
  });

  final AuthSessionController session;
  final AuthenticatedUser user;
  final DashboardRepository repository;

  @override
  State<DashboardShell> createState() => _DashboardShellState();
}

class _DashboardShellState extends State<DashboardShell> {
  late DashboardController _controller;
  int _selectedSection = 0;

  @override
  void initState() {
    super.initState();
    _controller = _createController();
    unawaited(_controller.refresh());
  }

  @override
  void didUpdateWidget(covariant DashboardShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.user != widget.user ||
        oldWidget.repository != widget.repository) {
      _controller.dispose();
      _controller = _createController();
      unawaited(_controller.refresh());
    }
  }

  DashboardController _createController() {
    final List<DashboardRole> roles = <DashboardRole>[];
    for (final String code in widget.user.availableRoles) {
      final DashboardRole? role = DashboardRole.fromCode(code);
      if (role != null && !roles.contains(role)) roles.add(role);
    }
    return DashboardController(
      repository: widget.repository,
      user: widget.user,
      roles: roles,
      initialRole: roles.isEmpty ? null : roles.first,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        return Scaffold(
          appBar: AppBar(title: const Text('ResQVision')),
          body: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth >= 720;
              final Widget content = _selectedSection == 0
                  ? _overviewForSelectedRole()
                  : _ProfileSummary(user: widget.user);
              final Widget main = Column(
                children: <Widget>[
                  _WorkspaceControls(
                    roles: _controller.roles,
                    selectedRole: _controller.selectedRole,
                    onSelectRole: _controller.selectRole,
                    onSignOut: () => unawaited(widget.session.logout()),
                  ),
                  Expanded(child: content),
                ],
              );
              final Widget constrainedMain = Align(
                alignment: Alignment.topCenter,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1040),
                  child: main,
                ),
              );
              if (!wide) return constrainedMain;
              return Row(
                children: <Widget>[
                  NavigationRail(
                    selectedIndex: _selectedSection,
                    labelType: NavigationRailLabelType.all,
                    onDestinationSelected: (int value) => setState(() {
                      _selectedSection = value;
                    }),
                    destinations: const <NavigationRailDestination>[
                      NavigationRailDestination(
                        icon: Icon(Icons.dashboard_outlined),
                        selectedIcon: Icon(Icons.dashboard),
                        label: Text('Overview'),
                      ),
                      NavigationRailDestination(
                        icon: Icon(Icons.person_outline),
                        selectedIcon: Icon(Icons.person),
                        label: Text('Profile'),
                      ),
                    ],
                  ),
                  const VerticalDivider(width: 1),
                  Expanded(child: constrainedMain),
                ],
              );
            },
          ),
          bottomNavigationBar: MediaQuery.sizeOf(context).width < 720
              ? NavigationBar(
                  selectedIndex: _selectedSection,
                  onDestinationSelected: (int value) => setState(() {
                    _selectedSection = value;
                  }),
                  destinations: const <NavigationDestination>[
                    NavigationDestination(
                      icon: Icon(Icons.dashboard_outlined),
                      selectedIcon: Icon(Icons.dashboard),
                      label: 'Overview',
                    ),
                    NavigationDestination(
                      icon: Icon(Icons.person_outline),
                      selectedIcon: Icon(Icons.person),
                      label: 'Profile',
                    ),
                  ],
                )
              : null,
        );
      },
    );
  }

  Widget _overviewForSelectedRole() {
    final DashboardRole? role = _controller.selectedRole;
    if (role == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.lg),
          child: AppEmptyState(
            title: 'Workspace unavailable',
            message:
                'This account has no supported human workspace. Sign out is still available.',
            icon: Icons.lock_outline,
          ),
        ),
      );
    }
    return switch (role) {
      DashboardRole.admin => AdminDashboardScreen(controller: _controller),
      DashboardRole.police => PoliceDashboardScreen(controller: _controller),
      DashboardRole.hospital => HospitalDashboardScreen(
        controller: _controller,
      ),
    };
  }
}

class _WorkspaceControls extends StatelessWidget {
  const _WorkspaceControls({
    required this.roles,
    required this.selectedRole,
    required this.onSelectRole,
    required this.onSignOut,
  });

  final List<DashboardRole> roles;
  final DashboardRole? selectedRole;
  final ValueChanged<DashboardRole> onSelectRole;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    final DashboardRole? role = selectedRole;
    final Widget roleControl;
    if (role == null) {
      roleControl = const Chip(label: Text('Workspace unavailable'));
    } else if (roles.length > 1) {
      roleControl = PopupMenuButton<DashboardRole>(
        tooltip: 'Switch workspace',
        onSelected: onSelectRole,
        itemBuilder: (BuildContext context) => roles
            .map(
              (DashboardRole item) => PopupMenuItem<DashboardRole>(
                value: item,
                child: Text('${item.code} workspace'),
              ),
            )
            .toList(growable: false),
        child: DashboardRoleBadge(role: role),
      );
    } else {
      roleControl = DashboardRoleBadge(role: role);
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.md,
        AppSpacing.sm,
        AppSpacing.md,
        0,
      ),
      child: Wrap(
        spacing: AppSpacing.sm,
        runSpacing: AppSpacing.xs,
        crossAxisAlignment: WrapCrossAlignment.center,
        alignment: WrapAlignment.spaceBetween,
        children: <Widget>[
          roleControl,
          TextButton.icon(
            onPressed: onSignOut,
            icon: const Icon(Icons.logout),
            label: const Text('Sign out'),
          ),
        ],
      ),
    );
  }
}

class _ProfileSummary extends StatelessWidget {
  const _ProfileSummary({required this.user});

  final AuthenticatedUser user;

  @override
  Widget build(BuildContext context) {
    final List<OrganizationMembership> memberships = user.memberships
        .where((OrganizationMembership item) => item.status == 'ACTIVE')
        .toList(growable: false);
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: <Widget>[
        Text('Profile', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                user.displayName,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(user.email),
              const SizedBox(height: AppSpacing.lg),
              const SectionHeading(title: 'Recognized workspaces'),
              const SizedBox(height: AppSpacing.sm),
              if (user.availableRoles.isEmpty)
                const Text(
                  'No supported human role was returned by ResQVision.',
                )
              else
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.xs,
                  children: <Widget>[
                    for (final String role in user.availableRoles)
                      Chip(label: Text(role)),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        SectionHeading(
          title: 'Active organization memberships',
          description:
              'Membership details returned in your authenticated profile.',
        ),
        const SizedBox(height: AppSpacing.md),
        if (memberships.isEmpty)
          const AppCard(
            child: Text('No active organization memberships are available.'),
          )
        else
          for (final OrganizationMembership membership
              in memberships) ...<Widget>[
            AppCard(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Icon(Icons.apartment_outlined),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          membership.organizationName,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          '${membership.organizationKind} · ${membership.organizationCode}',
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
      ],
    );
  }
}
