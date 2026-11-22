import 'package:flutter/material.dart';

import '../application/dashboard_controller.dart';
import '../data/dashboard_repository.dart';
import '../presentation/dashboard_overview_content.dart';

class HospitalDashboardScreen extends StatelessWidget {
  const HospitalDashboardScreen({super.key, required this.controller});

  final DashboardController controller;

  @override
  Widget build(BuildContext context) => DashboardOverviewContent(
    controller: controller,
    role: DashboardRole.hospital,
    sectionTitle: 'Assigned hospital incidents',
    description:
        'Incidents assigned to your active Hospital memberships. Review the current incident and assignment status within your authorized organization scope.',
  );
}
