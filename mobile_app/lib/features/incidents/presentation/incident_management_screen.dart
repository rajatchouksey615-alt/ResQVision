import 'dart:async';

import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/section_heading.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../../dashboard/data/dashboard_repository.dart';
import '../application/incident_list_controller.dart';
import '../data/incident_repository.dart';
import 'incident_detail_screen.dart';

class IncidentManagementScreen extends StatefulWidget {
  const IncidentManagementScreen({
    super.key,
    required this.repository,
    required this.role,
    required this.memberships,
    required this.organizationId,
  });

  final IncidentRepository repository;
  final DashboardRole role;
  final List<OrganizationMembership> memberships;
  final String? organizationId;

  @override
  State<IncidentManagementScreen> createState() =>
      _IncidentManagementScreenState();
}

class _IncidentManagementScreenState extends State<IncidentManagementScreen> {
  late IncidentListController _controller;

  @override
  void initState() {
    super.initState();
    _controller = _createController();
    unawaited(_controller.refresh());
  }

  @override
  void didUpdateWidget(covariant IncidentManagementScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.repository != widget.repository ||
        oldWidget.role != widget.role ||
        oldWidget.organizationId != widget.organizationId ||
        oldWidget.memberships != widget.memberships) {
      _controller.dispose();
      _controller = _createController();
      unawaited(_controller.refresh());
    }
  }

  IncidentListController _createController() => IncidentListController(
    repository: widget.repository,
    role: widget.role,
    memberships: widget.memberships,
    organizationId: widget.organizationId,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) => RefreshIndicator(
        onRefresh: _controller.refresh,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppSpacing.lg),
          children: <Widget>[
            SectionHeading(
              title: '${widget.role.title} incidents',
              description:
                  'Read-only incident records returned by your authorized backend scope. Search is not supported by the incident API; status filtering is applied by the backend.',
            ),
            const SizedBox(height: AppSpacing.md),
            _StatusFilter(
              value: _controller.selectedStatus,
              onChanged: _controller.setStatus,
            ),
            const SizedBox(height: AppSpacing.md),
            if (_controller.isLoading && _controller.incidents.isEmpty)
              const AppCard(
                child: Column(
                  children: <Widget>[
                    CircularProgressIndicator(),
                    SizedBox(height: AppSpacing.md),
                    Text('Loading authorized incidents…'),
                  ],
                ),
              )
            else if (_controller.error != null && _controller.incidents.isEmpty)
              AppErrorState(
                title: 'Incidents unavailable',
                message: _controller.error!,
                onRetry: _controller.refresh,
              )
            else ...<Widget>[
              if (_controller.isLoading)
                const Padding(
                  padding: EdgeInsets.only(bottom: AppSpacing.md),
                  child: LinearProgressIndicator(),
                ),
              if (_controller.pageError != null)
                AppCard(
                  child: Row(
                    children: <Widget>[
                      Expanded(child: Text(_controller.pageError!)),
                      TextButton(
                        onPressed: _controller.refresh,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
              if (_controller.incidents.isEmpty)
                AppEmptyState(
                  title: _controller.totalCount == 0
                      ? 'No incidents in your authorized scope'
                      : 'No matching assignment on this page',
                  message: _controller.totalCount == 0
                      ? 'The backend returned no incidents for this status filter and authenticated account.'
                      : 'The backend count covers your combined active memberships. This workspace narrows the visible assignments; continue to the next page to check the remaining authorized records.',
                  icon: Icons.inbox_outlined,
                  action: _controller.hasMore
                      ? _LoadMoreButton(controller: _controller)
                      : null,
                )
              else ...<Widget>[
                AppCard(
                  child: Text(
                    '${_controller.incidents.length} shown · backend count ${_controller.totalCount} in combined authorized scope${_controller.selectedStatus == null ? '' : ' · ${_statusLabel(_controller.selectedStatus!)}'}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                for (final ManagedIncident incident
                    in _controller.incidents) ...<Widget>[
                  _IncidentCard(
                    incident: incident,
                    onTap: () => _openIncident(incident),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                ],
                if (_controller.hasMore)
                  _LoadMoreButton(controller: _controller),
              ],
              if (_controller.isPartial)
                const Padding(
                  padding: EdgeInsets.only(top: AppSpacing.sm),
                  child: AppCard(
                    child: Text(
                      'Some assignment details changed during loading or continue beyond the bounded assignment page. Refresh to check current data.',
                    ),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }

  void _openIncident(ManagedIncident incident) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => IncidentDetailScreen(
          repository: widget.repository,
          incidentId: incident.id,
          role: widget.role,
          memberships: widget.memberships,
          organizationId: widget.organizationId,
        ),
      ),
    );
  }
}

class _StatusFilter extends StatelessWidget {
  const _StatusFilter({required this.value, required this.onChanged});

  final String? value;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => AppCard(
    child: DropdownButtonFormField<String?>(
      initialValue: value,
      decoration: const InputDecoration(
        labelText: 'Filter by incident status',
        border: OutlineInputBorder(),
      ),
      items: <DropdownMenuItem<String?>>[
        const DropdownMenuItem<String?>(
          value: null,
          child: Text('All statuses'),
        ),
        for (final String status in IncidentRepository.supportedStatuses)
          DropdownMenuItem<String?>(
            value: status,
            child: Text(_statusLabel(status)),
          ),
      ],
      onChanged: onChanged,
    ),
  );
}

class _IncidentCard extends StatelessWidget {
  const _IncidentCard({required this.incident, required this.onTap});

  final ManagedIncident incident;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
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
                Chip(label: Text(_statusLabel(incident.status))),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            Text('Created ${_dateLabel(incident.createdAt)}'),
            const SizedBox(height: AppSpacing.sm),
            for (final IncidentAssignment assignment in incident.assignments)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                child: Text(
                  '${assignment.organizationName} · ${_statusLabel(assignment.status)}',
                ),
              ),
            if (incident.assignmentsArePartial)
              const Text(
                'More assignment records are available on the backend.',
              ),
            const SizedBox(height: AppSpacing.sm),
            const Align(
              alignment: Alignment.centerRight,
              child: Text('View details →'),
            ),
          ],
        ),
      ),
    ),
  );
}

class _LoadMoreButton extends StatelessWidget {
  const _LoadMoreButton({required this.controller});

  final IncidentListController controller;

  @override
  Widget build(BuildContext context) => Align(
    alignment: Alignment.center,
    child: OutlinedButton.icon(
      onPressed: controller.isLoadingMore ? null : controller.loadMore,
      icon: controller.isLoadingMore
          ? const SizedBox.square(
              dimension: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.expand_more),
      label: Text(controller.isLoadingMore ? 'Loading…' : 'Load next page'),
    ),
  );
}

String _statusLabel(String status) => status
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
