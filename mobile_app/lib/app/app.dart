import 'package:flutter/material.dart';

import '../core/config/app_config.dart';
import '../core/errors/app_error.dart';
import '../features/dashboard/presentation/about_screen.dart';
import '../features/dashboard/presentation/foundation_home_screen.dart';
import 'router/app_router.dart';
import 'theme/app_theme.dart';

class ResQVisionApp extends StatelessWidget {
  const ResQVisionApp({super.key, required this.config, this.startupError});

  final AppConfig? config;
  final AppError? startupError;

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
        home: FoundationHomeScreen(
          startupError: startupError,
          hasConfiguration: config != null,
        ),
        about: const AboutScreen(),
      ),
      onUnknownRoute: AppRouter.onUnknownRoute,
    );
  }
}
