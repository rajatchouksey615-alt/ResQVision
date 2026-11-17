import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/app.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/errors/app_error.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';

void main() {
  Widget createApp() => ResQVisionApp(
    config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
  );

  testWidgets('shows the foundation home and navigates to About', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(createApp());

    expect(find.text('Mobile application foundation'), findsOneWidget);
    expect(
      find.text(
        'No emergency dispatch or police, hospital, or ambulance alerts are connected.',
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('About this prototype'));
    await tester.pumpAndSettle();

    expect(
      find.text(
        'ResQVision is an academic prototype for road accident detection and emergency response coordination. The mobile app is a foundation shell; authentication and incident workflows are outside this phase.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('routes unknown paths safely without echoing route values', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(createApp());
    final BuildContext context = tester.element(
      find.text('Mobile application foundation'),
    );
    Navigator.of(context).pushNamed('/missing?token=private-value');
    await tester.pumpAndSettle();

    expect(find.text('Page not found'), findsOneWidget);
    expect(find.text('This page is not available.'), findsOneWidget);
    expect(find.textContaining('private-value'), findsNothing);

    await tester.tap(find.text('Go to home'));
    await tester.pumpAndSettle();
    expect(find.text('Mobile application foundation'), findsOneWidget);
  });

  testWidgets('shows a friendly setup state when configuration is invalid', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ResQVisionApp(
        config: null,
        startupError: const AppError(
          kind: AppErrorKind.configuration,
          message: 'Set API_BASE_URL and restart.',
        ),
      ),
    );

    expect(find.text('App setup required'), findsOneWidget);
    expect(find.text('Set API_BASE_URL and restart.'), findsOneWidget);
  });
}
