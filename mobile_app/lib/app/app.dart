import 'package:flutter/material.dart';

import '../core/config/app_config.dart';
import '../core/errors/app_error.dart';
import '../features/authentication/application/auth_session_controller.dart';
import '../features/authentication/presentation/session_gate.dart';
import '../features/dashboard/data/dashboard_repository.dart';
import '../features/dashboard/presentation/about_screen.dart';
import '../features/dashboard/presentation/foundation_home_screen.dart';
import 'router/app_router.dart';
import 'theme/app_theme.dart';

class ResQVisionApp extends StatelessWidget {
  const ResQVisionApp({
    super.key,
    required this.config,
    this.startupError,
    this.sessionController,
    this.dashboardRepository,
  });

  final AppConfig? config;
  final AppError? startupError;
  final AuthSessionController? sessionController;
  final DashboardRepository? dashboardRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ResQVision',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      initialRoute: AppRoutes.home,
      onGenerateRoute: (RouteSettings settings) => AppRouter.onGenerateRoute(
        settings,
        home: config == null || sessionController == null
            ? FoundationHomeScreen(
                startupError: startupError,
                hasConfiguration: false,
              )
            : SessionGate(
                session: sessionController!,
                dashboardRepository: dashboardRepository,
              ),
        about: const AboutScreen(),
      ),
      onUnknownRoute: AppRouter.onUnknownRoute,
    );
  }
}
