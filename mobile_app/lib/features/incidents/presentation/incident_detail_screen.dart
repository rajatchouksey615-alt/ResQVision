import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/section_heading.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../../dashboard/data/dashboard_repository.dart';
import '../data/incident_repository.dart';

class IncidentDetailScreen extends StatefulWidget {
  const IncidentDetailScreen({
    super.key,
    required this.repository,
    required this.incidentId,
    required this.role,
    required this.memberships,
    required this.organizationId,
  });

  final IncidentRepository repository;
  final String incidentId;
  final DashboardRole role;
  final List<OrganizationMembership> memberships;
  final String? organizationId;

  @override
  State<IncidentDetailScreen> createState() => _IncidentDetailScreenState();
}

class _IncidentDetailScreenState extends State<IncidentDetailScreen> {
  late Future<ManagedIncidentDetail> _detail;

  @override
  void initState() {
    super.initState();
    _detail = _load();
  }

  Future<ManagedIncidentDetail> _load() => widget.repository.loadDetail(
    incidentId: widget.incidentId,
    role: widget.role,
    activeMemberships: widget.memberships,
    organizationId: widget.organizationId,
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Incident details')),
    body: FutureBuilder<ManagedIncidentDetail>(
      future: _detail,
      builder:
          (
            BuildContext context,
            AsyncSnapshot<ManagedIncidentDetail> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    CircularProgressIndicator(),
                    SizedBox(height: AppSpacing.md),
                    Text('Loading authorized incident details…'),
                  ],
                ),
              );
            }
            if (snapshot.hasError || !snapshot.hasData) {
              final Object? error = snapshot.error;
              return AppErrorState(
                title: 'Incident details unavailable',
                message: error is IncidentDataException
                    ? error.message
                    : 'Incident details could not be loaded. Try again.',
                onRetry: () => setState(() => _detail = _load()),
              );
            }
            return _IncidentDetailContent(detail: snapshot.data!);
          },
    ),
  );
}

class _IncidentDetailContent extends StatelessWidget {
  const _IncidentDetailContent({required this.detail});

  final ManagedIncidentDetail detail;

  @override
  Widget build(BuildContext context) {
    final ManagedIncident incident = detail.incident;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: <Widget>[
        SectionHeading(
          title: 'Incident · ${incident.id.substring(0, 8)}',
          description:
              'Authoritative incident summary returned by the backend. This page does not change incident state.',
        ),
        const SizedBox(height: AppSpacing.md),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _DetailRow(label: 'Incident ID', value: incident.id),
              _DetailRow(label: 'Status', value: _label(incident.status)),
              _DetailRow(
                label: 'Created',
                value: _dateLabel(incident.createdAt),
              ),
              _DetailRow(
                label: 'Last updated',
                value: _dateLabel(incident.updatedAt),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        SectionHeading(
          title: 'Visible response assignments',
          description:
              'Only assignments returned within your active role and organization memberships appear here.',
        ),
        const SizedBox(height: AppSpacing.sm),
        if (detail.assignments.isEmpty)
          const AppEmptyState(
            title: 'No assignments in this workspace',
            message:
                'The backend did not return a response assignment for the selected role and organization context.',
            icon: Icons.assignment_outlined,
          )
        else
          for (final IncidentAssignment assignment
              in detail.assignments) ...<Widget>[
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    assignment.organizationName,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    '${assignment.organizationKind} · ${_label(assignment.status)}',
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text('Assignment · ${assignment.id.substring(0, 8)}'),
                  Text('Created ${_dateLabel(assignment.createdAt)}'),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        if (detail.assignmentsArePartial)
          const Padding(
            padding: EdgeInsets.only(top: AppSpacing.sm),
            child: AppCard(
              child: Text(
                'The backend assignment page is bounded. Additional assignments may exist; refresh after the assignment policy supports full access.',
              ),
            ),
          ),
        const SizedBox(height: AppSpacing.lg),
        const SectionHeading(title: 'Location information unavailable'),
        const SizedBox(height: AppSpacing.sm),
        const AppCard(
          child: Text(
            'The incident location endpoint is policy-blocked by the backend (503). No coordinates, camera position, or location provenance are available to display.',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        const SectionHeading(title: 'Evidence information unavailable'),
        const SizedBox(height: AppSpacing.sm),
        const AppCard(
          child: Text(
            'Evidence metadata and retrieval endpoints are policy-blocked by the backend (503). No storage paths or private media links are exposed.',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        const AppCard(
          child: Text(
            'Incident lifecycle actions are not available in this app. Resolve and close routes currently fail closed pending approved authority policies.',
          ),
        ),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(
          width: 112,
          child: Text(label, style: Theme.of(context).textTheme.bodySmall),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(child: SelectableText(value)),
      ],
    ),
  );
}

String _label(String status) => status
    .split('_')
    .map(
      (String word) =>
          word.isEmpty ? word : '${word[0]}${word.substring(1).toLowerCase()}',
    )
    .join(' ');

String _dateLabel(DateTime dateTime) {
  final DateTime local = dateTime.toLocal();
  final String month = local.month.toString().padLeft(2, '0');
  final String day = local.day.toString().padLeft(2, '0');
  final String hour = local.hour.toString().padLeft(2, '0');
  final String minute = local.minute.toString().padLeft(2, '0');
  return '${local.year}-$month-$day · $hour:$minute';
}
