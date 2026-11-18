import 'package:flutter/material.dart';

import '../application/dashboard_controller.dart';
import '../data/dashboard_repository.dart';
import '../presentation/dashboard_overview_content.dart';

class AdminDashboardScreen extends StatelessWidget {
  const AdminDashboardScreen({super.key, required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) => DashboardOverviewContent(
    controller: controller,
    role: DashboardRole.admin,
    sectionTitle: 'Incident overview',
    description:
        'Read-only operational information within your own authorized assignment scope. No system-wide summary API is available.',
  );
}
