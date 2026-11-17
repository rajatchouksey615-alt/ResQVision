import 'package:flutter/material.dart';

import '../../../app/router/app_router.dart';
import '../../../app/theme/app_spacing.dart';
import '../../../core/errors/app_error.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/section_heading.dart';

class FoundationHomeScreen extends StatelessWidget {
  const FoundationHomeScreen({
    super.key,
    this.startupError,
    required this.hasConfiguration,
  });

  final AppError? startupError;
  final bool hasConfiguration;

  @override
  Widget build(BuildContext context) {
    if (startupError != null || !hasConfiguration) {
      return Scaffold(
        appBar: AppBar(title: const Text('ResQVision')),
        body: AppErrorState(
          title: 'App setup required',
          message:
              startupError?.message ??
              'App configuration is unavailable. Check API_BASE_URL and restart.',
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('ResQVision')),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double contentWidth = constraints.maxWidth > 760
                ? 680
                : constraints.maxWidth;
            return SingleChildScrollView(
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: contentWidth),
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Mobile application foundation',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Text(
                          'A clean starting point for the ResQVision client.',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: AppSpacing.lg),
                        AppCard(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              const SectionHeading(
                                title: 'Prototype status',
                                description:
                                    'This app currently provides its application shell and shared foundations.',
                              ),
                              const SizedBox(height: AppSpacing.md),
                              Text(
                                'No emergency dispatch or police, hospital, or ambulance alerts are connected.',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppSpacing.lg),
                        AppButton(
                          label: 'About this prototype',
                          onPressed: () =>
                              Navigator.of(context).pushNamed(AppRoutes.about),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
