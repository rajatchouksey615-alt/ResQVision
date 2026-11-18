import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../data/dashboard_repository.dart';

class DashboardMetricCard extends StatelessWidget {
  const DashboardMetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.caption,
  });

  final String label;
  final String value;
  final IconData icon;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return AppCard(
      child: SizedBox(
        width: 240,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, color: colors.primary),
            const SizedBox(height: AppSpacing.md),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: AppSpacing.xs),
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            if (caption != null) ...<Widget>[
              const SizedBox(height: AppSpacing.xs),
              Text(caption!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}

class DashboardRoleBadge extends StatelessWidget {
  const DashboardRoleBadge({super.key, required this.role});

  final DashboardRole role;

  @override
  Widget build(BuildContext context) {
    final (IconData icon, String label) = switch (role) {
      DashboardRole.admin => (Icons.admin_panel_settings_outlined, 'ADMIN'),
      DashboardRole.police => (Icons.local_police_outlined, 'POLICE'),
      DashboardRole.hospital => (Icons.local_hospital_outlined, 'HOSPITAL'),
    };
    return Chip(avatar: Icon(icon, size: 18), label: Text('$label workspace'));
  }
}

String dashboardStatusLabel(String status) => status
    .split('_')
    .map(
      (String word) =>
          word.isEmpty ? word : '${word[0]}${word.substring(1).toLowerCase()}',
    )
    .join(' ');

String dashboardDateLabel(DateTime dateTime) {
  final DateTime local = dateTime.toLocal();
  final String month = local.month.toString().padLeft(2, '0');
  final String day = local.day.toString().padLeft(2, '0');
  final String hour = local.hour.toString().padLeft(2, '0');
  final String minute = local.minute.toString().padLeft(2, '0');
  return '${local.year}-$month-$day · $hour:$minute';
}

class DashboardIncidentCard extends StatelessWidget {
  const DashboardIncidentCard({super.key, required this.incident});

  final DashboardIncident incident;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.xs,
            children: <Widget>[
              Text(
                'Incident · ${incident.id.substring(0, 8)}',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              Chip(label: Text(dashboardStatusLabel(incident.status))),
            ],
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Created ${dashboardDateLabel(incident.createdAt)}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          for (final DashboardAssignment assignment in incident.assignments)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Icon(Icons.assignment_outlined, size: 18),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      '${assignment.organizationName} · ${dashboardStatusLabel(assignment.status)}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
