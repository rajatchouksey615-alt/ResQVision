import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/app/app.dart';
import 'package:resqvision_mobile/core/config/app_config.dart';
import 'package:resqvision_mobile/core/networking/api_request.dart';

import '../support/auth_test_support.dart';

void main() {
  testWidgets(
    'startup shows a loading gate until stored credentials are checked',
    (WidgetTester tester) async {
      final AuthHarness harness = _successfulHarness();
      await tester.pumpWidget(_app(harness));
      expect(find.text('Checking your session…'), findsOneWidget);

      await harness.session.restoreSession();
      await tester.pumpAndSettle();
      expect(find.text('Sign in to ResQVision'), findsOneWidget);
      harness.close();
    },
  );

  testWidgets(
    'login validates fields, toggles password visibility, and loads backend workspace',
    (WidgetTester tester) async {
      final AuthHarness harness = _successfulHarness();
      await harness.session.restoreSession();
      await tester.pumpWidget(_app(harness));

      await tester.ensureVisible(find.text('Sign in'));
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(find.text('Enter your email address.'), findsOneWidget);
      expect(find.text('Enter your password.'), findsOneWidget);

      await tester.enterText(
        find.byType(TextFormField).at(0),
        'reviewer@example.test',
      );
      await tester.enterText(
        find.byType(TextFormField).at(1),
        'correct-horse-battery',
      );
      expect(_passwordIsObscured(tester), isTrue);
      await tester.tap(find.byTooltip('Show password'));
      await tester.pump();
      expect(_passwordIsObscured(tester), isFalse);

      await tester.ensureVisible(find.text('Sign in'));
      await tester.tap(find.text('Sign in'));
      await tester.pumpAndSettle();
      expect(find.text('Welcome, Rajat Reviewer'), findsOneWidget);
      expect(find.text('POLICE workspace'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Central Police · central-police'),
        200,
        scrollable: find
            .descendant(
              of: find.byType(RefreshIndicator),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      expect(find.text('Central Police · central-police'), findsOneWidget);
      harness.close();
    },
  );

  testWidgets('login failures use safe messages and logout clears the session', (
    WidgetTester tester,
  ) async {
    final AuthHarness harness = AuthHarness(
      transport: ScriptedTransport((ApiRequest request) async {
        if (request.uri.path.endsWith('/auth/token/')) {
          return jsonResponse(
            401,
            '{"code":"authentication_failed","detail":"private backend detail"}',
          );
        }
        throw StateError('Profile must not be requested after failed login.');
      }),
    );
    await harness.session.restoreSession();
    await tester.pumpWidget(_app(harness));
    await tester.enterText(
      find.byType(TextFormField).at(0),
      'reviewer@example.test',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'wrong-password');
    await tester.ensureVisible(find.text('Sign in'));
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Email or password is incorrect.'), findsOneWidget);
    expect(find.textContaining('private backend detail'), findsNothing);

    harness.close();
  });

  testWidgets('logout returns to login and reports unconfirmed revocation', (
    WidgetTester tester,
  ) async {
    final ScriptedTransport transport = ScriptedTransport((
      ApiRequest request,
    ) async {
      if (request.uri.path.endsWith('/auth/token/')) {
        return tokenResponse(loginTokens);
      }
      if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
      if (request.uri.path.endsWith('/auth/logout/')) {
        return jsonResponse(503, '{}');
      }
      if (request.uri.path.endsWith('/incidents/')) {
        return jsonResponse(
          200,
          '{"count":0,"next":null,"previous":null,"results":[]}',
        );
      }
      throw StateError('Unexpected request path.');
    });
    final AuthHarness harness = AuthHarness(transport: transport);
    await harness.session.restoreSession();
    await tester.pumpWidget(_app(harness));
    await tester.enterText(
      find.byType(TextFormField).at(0),
      'reviewer@example.test',
    );
    await tester.enterText(
      find.byType(TextFormField).at(1),
      'correct-password',
    );
    await tester.ensureVisible(find.text('Sign in'));
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('POLICE workspace'), findsOneWidget);

    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();

    expect(find.text('Sign in to ResQVision'), findsOneWidget);
    expect(
      find.text(
        'You are signed out on this device. The server could not confirm session revocation.',
      ),
      findsOneWidget,
    );
    expect(harness.storage.tokens, isNull);
    harness.close();
  });
}

AuthHarness _successfulHarness() => AuthHarness(
  transport: ScriptedTransport((ApiRequest request) async {
    if (request.uri.path.endsWith('/auth/token/')) {
      return tokenResponse(loginTokens);
    }
    if (request.uri.path.endsWith('/auth/me/')) return profileResponse();
    if (request.uri.path.endsWith('/auth/logout/')) {
      return jsonResponse(204, '');
    }
    if (request.uri.path.endsWith('/incidents/')) {
      return jsonResponse(
        200,
        '{"count":0,"next":null,"previous":null,"results":[]}',
      );
    }
    throw StateError('Unexpected request path.');
  }),
);

ResQVisionApp _app(AuthHarness harness) => ResQVisionApp(
  config: AppConfig.fromValues(apiBaseUrl: 'http://127.0.0.1:8000/api/v1/'),
  sessionController: harness.session,
  dashboardRepository: harness.dashboardRepository,
);

bool _passwordIsObscured(WidgetTester tester) =>
    tester.widget<EditableText>(find.byType(EditableText).last).obscureText;
