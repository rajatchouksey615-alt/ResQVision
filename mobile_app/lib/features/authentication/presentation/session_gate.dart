import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_loading_state.dart';
import '../application/auth_session_controller.dart';
import 'login_screen.dart';
import 'role_landing_screen.dart';

class SessionGate extends StatelessWidget {
  const SessionGate({super.key, required this.session});

  final AuthSessionController session;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: session,
      builder: (BuildContext context, Widget? child) {
        switch (session.status) {
          case SessionStatus.initializing:
            return const Scaffold(
              body: SafeArea(
                child: AppLoadingState(message: 'Checking your session…'),
              ),
            );
          case SessionStatus.authenticating:
          case SessionStatus.unauthenticated:
            return LoginScreen(session: session);
          case SessionStatus.sessionExpired:
            return LoginScreen(
              session: session,
              sessionMessage: 'Your session ended. Sign in to continue.',
            );
          case SessionStatus.authenticated:
          case SessionStatus.refreshing:
            final user = session.user;
            if (user == null) {
              return const Scaffold(
                body: SafeArea(
                  child: AppLoadingState(message: 'Restoring your session…'),
                ),
              );
            }
            return RoleLandingScreen(session: session, user: user);
          case SessionStatus.recoverableError:
            if (session.user != null) {
              return RoleLandingScreen(session: session, user: session.user!);
            }
            return _SessionRecoveryScreen(session: session);
        }
      },
    );
  }
}

class _SessionRecoveryScreen extends StatelessWidget {
  const _SessionRecoveryScreen({required this.session});

  final AuthSessionController session;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ResQVision')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  const Icon(Icons.wifi_off_outlined, size: 44),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    'Could not restore your session',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    session.error?.message ??
                        'Check your connection and try again.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  AppButton(
                    label: 'Try again',
                    onPressed: () => session.restoreSession(),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  OutlinedButton(
                    onPressed: () => session.signInAgain(),
                    child: const Text('Sign in with another account'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
