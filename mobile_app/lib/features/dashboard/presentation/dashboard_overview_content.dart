import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/section_heading.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../application/dashboard_controller.dart';
import '../data/dashboard_repository.dart';
import 'dashboard_widgets.dart';

class DashboardOverviewContent extends StatelessWidget {
  const DashboardOverviewContent({
    super.key,
    required this.controller,
    required this.role,
    required this.sectionTitle,
    required this.description,
  });

  final DashboardController controller;
  final DashboardRole role;
  final String sectionTitle;
  final String description;

  @override
  Widget build(BuildContext context) {
    final List<OrganizationMembership> memberships =
        controller.organizationOptions;
    return RefreshIndicator(
      onRefresh: controller.refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: <Widget>[
          Text(
            'Welcome, ${controller.user.displayName}',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            controller.user.email,
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: AppSpacing.lg),
          SectionHeading(
            title: '${role.title} overview',
            description: description,
          ),
          const SizedBox(height: AppSpacing.md),
          Wrap(
            spacing: AppSpacing.md,
            runSpacing: AppSpacing.md,
            children: <Widget>[
              DashboardMetricCard(
                label: 'Active organizations',
                value: memberships.length.toString(),
                icon: Icons.apartment_outlined,
                caption: 'From your authenticated profile',
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          SectionHeading(
            title: sectionTitle,
            description:
                'Paginated read-only preview from your authorized ResQVision scope. Up to ${DashboardRepository.pageSize} incident summaries appear per page; load the next page to continue. This is not a system-wide total.',
          ),
          const SizedBox(height: AppSpacing.md),
          if (controller.workspaceUnavailable)
            const AppEmptyState(
              title: 'Workspace unavailable',
              message:
                  'This role has no active matching organization membership. Contact your organization administrator.',
              icon: Icons.lock_outline,
            )
          else if (controller.isLoading && controller.incidents.isEmpty)
            const SizedBox(
              height: 240,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    CircularProgressIndicator(),
                    SizedBox(height: AppSpacing.md),
                    Text('Loading authorized incident summaries…'),
                  ],
                ),
              ),
            )
          else if (controller.error != null && controller.incidents.isEmpty)
            AppErrorState(
              title: 'Dashboard data unavailable',
              message: controller.error!,
              onRetry: controller.refresh,
            )
          else ...<Widget>[
            if (controller.pageError != null)
              AppCard(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Icon(
                      Icons.warning_amber_outlined,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(child: Text(controller.pageError!)),
                    TextButton(
                      onPressed: controller.refresh,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            if (controller.isRefreshing)
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.md),
                child: LinearProgressIndicator(),
              ),
            if (controller.isPartial)
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.md),
                child: AppCard(
                  child: Text(
                    'Some assignment details changed during loading or continue beyond the bounded API page. Refresh to check for current data.',
                  ),
                ),
              ),
            if (controller.incidents.isEmpty)
              AppEmptyState(
                title: controller.totalCount == 0
                    ? 'No incidents in your authorized scope'
                    : 'No matching assignments on this page',
                message: controller.totalCount == 0
                    ? 'No incident summaries are currently available through your active organization assignments.'
                    : 'The latest incident summaries returned for this account do not include a ${role.title.toLowerCase()} assignment in this organization context.',
                icon: Icons.inbox_outlined,
                action: controller.hasMore
                    ? OutlinedButton.icon(
                        onPressed: controller.isLoadingMore
                            ? null
                            : controller.loadMore,
                        icon: controller.isLoadingMore
                            ? const SizedBox.square(
                                dimension: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.expand_more),
                        label: const Text('Load next page'),
                      )
                    : null,
              )
            else ...<Widget>[
              for (final incident in controller.incidents) ...<Widget>[
                DashboardIncidentCard(incident: incident),
                const SizedBox(height: AppSpacing.md),
              ],
              if (controller.hasMore)
                Align(
                  alignment: Alignment.center,
                  child: OutlinedButton.icon(
                    onPressed: controller.isLoadingMore
                        ? null
                        : controller.loadMore,
                    icon: controller.isLoadingMore
                        ? const SizedBox.square(
                            dimension: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.expand_more),
                    label: Text(
                      controller.isLoadingMore ? 'Loading…' : 'Load next page',
                    ),
                  ),
                ),
            ],
          ],
          const SizedBox(height: AppSpacing.lg),
          SectionHeading(
            title: 'Organization context',
            description: role == DashboardRole.admin
                ? 'These are your active memberships. Admin status does not expand incident access.'
                : 'Only active ${role.title.toLowerCase()} memberships are used in this workspace.',
          ),
          const SizedBox(height: AppSpacing.md),
          _OrganizationContext(
            controller: controller,
            memberships: memberships,
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

class _OrganizationContext extends StatelessWidget {
  const _OrganizationContext({
    required this.controller,
    required this.memberships,
  });

  final DashboardController controller;
  final List<OrganizationMembership> memberships;

  @override
  Widget build(BuildContext context) {
    if (memberships.isEmpty) {
      return AppCard(
        child: Text(
          controller.selectedRole == DashboardRole.admin
              ? 'No active organization memberships were returned for this account.'
              : 'No active organization membership is available for this workspace.',
        ),
      );
    }
    if (controller.hasOrganizationSelector) {
      return AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text('Filter this view by membership'),
            const SizedBox(height: AppSpacing.sm),
            DropdownButton<String?>(
              value: controller.selectedOrganizationId,
              isExpanded: true,
              items: <DropdownMenuItem<String?>>[
                const DropdownMenuItem<String?>(
                  value: null,
                  child: Text('All active organizations'),
                ),
                for (final OrganizationMembership membership in memberships)
                  DropdownMenuItem<String?>(
                    value: membership.organizationId,
                    child: Text(
                      '${membership.organizationName} · ${membership.organizationCode}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: controller.selectOrganization,
            ),
          ],
        ),
      );
    }
    final OrganizationMembership membership = memberships.single;
    return AppCard(
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
                  '${membership.organizationName} · ${membership.organizationCode}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text('${membership.organizationKind} membership'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
