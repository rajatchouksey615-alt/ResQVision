import 'package:flutter/material.dart';

import '../application/dashboard_controller.dart';
import '../data/dashboard_repository.dart';
import '../presentation/dashboard_overview_content.dart';

class PoliceDashboardScreen extends StatelessWidget {
  const PoliceDashboardScreen({super.key, required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) => DashboardOverviewContent(
    controller: controller,
    role: DashboardRole.police,
    sectionTitle: 'Assigned police incidents',
    description:
        'Read-only incident and response assignment information for active police memberships.',
  );
}
