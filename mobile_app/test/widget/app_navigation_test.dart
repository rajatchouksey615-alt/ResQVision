import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/app.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/errors/app_error.dart';
import 'package:resqvision_mobile/core/errors/app_exception.dart';

import '../support/auth_test_support.dart';

void main() {
  testWidgets('shows login and navigates to About', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = _emptySession();
    await harness.session.restoreSession();
    await tester.pumpWidget(_app(harness));

    expect(find.text('Sign in to ResQVision'), findsOneWidget);
    expect(find.byType(TextFormField), findsNWidgets(2));

    await tester.ensureVisible(find.text('About this prototype'));
    await tester.tap(find.text('About this prototype'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining(
        'This phase adds secure account sign-in and session handling',
      ),
      findsOneWidget,
    );

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('Sign in to ResQVision'), findsOneWidget);
    harness.close();
  });

  testWidgets('routes unknown paths safely without echoing route values', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = _emptySession();
    await harness.session.restoreSession();
    await tester.pumpWidget(_app(harness));
    final BuildContext context = tester.element(
      find.text('Sign in to ResQVision'),
    );
    Navigator.of(context).pushNamed('/missing?token=private-value');
    await tester.pumpAndSettle();

    expect(find.text('Page not found'), findsOneWidget);
    expect(find.text('This page is not available.'), findsOneWidget);
    expect(find.textContaining('private-value'), findsNothing);

    await tester.tap(find.text('Go to home'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in to ResQVision'), findsOneWidget);
    harness.close();
  });

  testWidgets('shows a friendly setup state when configuration is invalid', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const ResQVisionApp(
        config: null,
        startupError: AppError(
          kind: AppErrorKind.configuration,
          message: 'Set API_BASE_URL and restart.',
        ),
      ),
    );

    expect(find.text('App setup required'), findsOneWidget);
    expect(find.text('Set API_BASE_URL and restart.'), findsOneWidget);
  });
}

AuthHarness _emptySession() => AuthHarness(
  transport: ScriptedTransport(
    (request) async => throw StateError('No API request expected.'),
  ),
);

ResQVisionApp _app(AuthHarness harness) => ResQVisionApp(
  config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
  sessionController: harness.session,
  dashboardRepository: harness.dashboardRepository,
);
