import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/theme/app_theme.dart';
import 'package:resqvision_mobile/core/widgets/app_button.dart';
import 'package:resqvision_mobile/core/widgets/app_card.dart';
import 'package:resqvision_mobile/core/widgets/app_empty_state.dart';
import 'package:resqvision_mobile/core/widgets/app_error_state.dart';
import 'package:resqvision_mobile/core/widgets/app_loading_state.dart';
import 'package:resqvision_mobile/core/widgets/app_text_field.dart';

void main() {
  testWidgets('theme tokens support system dark mode', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeMode: ThemeMode.dark,
        home: const Scaffold(body: Text('Dark theme')),
      ),
    );

    final BuildContext context = tester.element(find.text('Dark theme'));
    expect(Theme.of(context).brightness, Brightness.dark);
  });

  testWidgets('loading state announces progress and renders its message', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: AppLoadingState(message: 'Loading incidents')),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.text('Loading incidents'), findsOneWidget);
  });

  testWidgets('empty state renders its content and optional action', (
    WidgetTester tester,
  ) async {
    var actionTapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppEmptyState(
            title: 'Nothing here yet',
            message: 'Items will appear when available.',
            action: AppButton(
              label: 'Refresh',
              onPressed: () => actionTapped = true,
            ),
          ),
        ),
      ),
    );

    expect(find.text('Nothing here yet'), findsOneWidget);
    expect(find.text('Items will appear when available.'), findsOneWidget);
    await tester.tap(find.text('Refresh'));
    expect(actionTapped, isTrue);
  });

  testWidgets('error state invokes retry when provided', (
    WidgetTester tester,
  ) async {
    var retryTapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppErrorState(
            title: 'Could not load',
            message: 'Check the connection.',
            onRetry: () => retryTapped = true,
          ),
        ),
      ),
    );

    await tester.tap(find.text('Try again'));
    expect(retryTapped, isTrue);
  });

  testWidgets('shared card and text field remain usable', (
    WidgetTester tester,
  ) async {
    final TextEditingController controller = TextEditingController();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppCard(
            child: AppTextField(label: 'Reference', controller: controller),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextFormField), 'sample-value');
    expect(controller.text, 'sample-value');
    expect(find.byType(Card), findsOneWidget);
    controller.dispose();
  });
}
