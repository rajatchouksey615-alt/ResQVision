import 'package:flutter/material.dart';

import '../../core/widgets/app_button.dart';
import '../theme/app_spacing.dart';

abstract final class AppRoutes {
  static const String home = '/';
  static const String login = '/login';
  static const String about = '/about';
}

abstract final class AppRouter {
  static Route<dynamic> onGenerateRoute(
    RouteSettings settings, {
    required Widget home,
    required Widget about,
  }) {
    final Widget page = switch (settings.name) {
      AppRoutes.home => home,
      AppRoutes.login => home,
      AppRoutes.about => about,
      _ => const UnknownRouteScreen(),
    };

    return MaterialPageRoute<void>(settings: settings, builder: (_) => page);
  }

  static Route<dynamic> onUnknownRoute(RouteSettings settings) {
    return MaterialPageRoute<void>(
      settings: settings,
      builder: (_) => const UnknownRouteScreen(),
    );
  }
}

class UnknownRouteScreen extends StatelessWidget {
  const UnknownRouteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Page not found')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.route_outlined, size: 40),
              const SizedBox(height: AppSpacing.md),
              Text(
                'This page is not available.',
                style: Theme.of(context).textTheme.bodyLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.lg),
              AppButton(
                label: 'Go to home',
                onPressed: () => Navigator.of(context).pushNamedAndRemoveUntil(
                  AppRoutes.home,
                  (Route<dynamic> route) => false,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
