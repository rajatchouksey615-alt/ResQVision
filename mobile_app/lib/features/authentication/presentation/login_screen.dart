import 'package:flutter/material.dart';

import '../../../app/router/app_router.dart';
import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_button.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_text_field.dart';
import '../../../core/widgets/section_heading.dart';
import '../application/auth_session_controller.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.session, this.sessionMessage});

  final AuthSessionController session;
  final String? sessionMessage;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _email = TextEditingController();
  final TextEditingController _password = TextEditingController();
  final FocusNode _passwordFocus = FocusNode();
  bool _showPassword = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    await widget.session.login(email: _email.text, password: _password.text);
  }

  @override
  Widget build(BuildContext context) {
    final bool busy = widget.session.status == SessionStatus.authenticating;
    final String? message =
        widget.session.error?.message ??
        widget.sessionMessage ??
        widget.session.logoutNotice;
    final ColorScheme colors = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('ResQVision')),
      body: SafeArea(
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final double width = constraints.maxWidth > 760
                ? 480
                : constraints.maxWidth;
            return SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: width),
                  child: AutofillGroup(
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: <Widget>[
                          const SizedBox(height: AppSpacing.xl),
                          Icon(
                            Icons.health_and_safety_outlined,
                            size: 52,
                            color: colors.primary,
                            semanticLabel: 'ResQVision',
                          ),
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            'Sign in to ResQVision',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.headlineMedium,
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            'Use your organization account to continue.',
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodyLarge,
                          ),
                          const SizedBox(height: AppSpacing.xl),
                          AppCard(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: <Widget>[
                                const SectionHeading(
                                  title: 'Account sign-in',
                                  description:
                                      'Your credentials are checked securely by ResQVision.',
                                ),
                                const SizedBox(height: AppSpacing.lg),
                                AppTextField(
                                  label: 'Email',
                                  controller: _email,
                                  keyboardType: TextInputType.emailAddress,
                                  textCapitalization: TextCapitalization.none,
                                  textInputAction: TextInputAction.next,
                                  autofillHints: const <String>[
                                    AutofillHints.username,
                                  ],
                                  autocorrect: false,
                                  enabled: !busy,
                                  onChanged: (_) => widget.session.clearError(),
                                  onFieldSubmitted: (_) =>
                                      _passwordFocus.requestFocus(),
                                  validator: (String? value) {
                                    final String email = (value ?? '').trim();
                                    if (email.isEmpty) {
                                      return 'Enter your email address.';
                                    }
                                    if (!RegExp(
                                      r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
                                    ).hasMatch(email)) {
                                      return 'Enter a valid email address.';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: AppSpacing.md),
                                AppTextField(
                                  label: 'Password',
                                  controller: _password,
                                  obscureText: !_showPassword,
                                  textInputAction: TextInputAction.done,
                                  autofillHints: const <String>[
                                    AutofillHints.password,
                                  ],
                                  autocorrect: false,
                                  enabled: !busy,
                                  suffixIcon: IconButton(
                                    tooltip: _showPassword
                                        ? 'Hide password'
                                        : 'Show password',
                                    onPressed: busy
                                        ? null
                                        : () => setState(
                                            () =>
                                                _showPassword = !_showPassword,
                                          ),
                                    icon: Icon(
                                      _showPassword
                                          ? Icons.visibility_off_outlined
                                          : Icons.visibility_outlined,
                                    ),
                                  ),
                                  onChanged: (_) => widget.session.clearError(),
                                  onFieldSubmitted: (_) => _submit(),
                                  validator: (String? value) =>
                                      value == null || value.isEmpty
                                      ? 'Enter your password.'
                                      : null,
                                ),
                                if (message != null) ...<Widget>[
                                  const SizedBox(height: AppSpacing.md),
                                  Semantics(
                                    liveRegion: true,
                                    child: Text(
                                      message,
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodyMedium
                                          ?.copyWith(color: colors.error),
                                    ),
                                  ),
                                ],
                                const SizedBox(height: AppSpacing.lg),
                                AppButton(
                                  label: busy ? 'Signing in…' : 'Sign in',
                                  onPressed: busy ? null : _submit,
                                ),
                                if (busy) ...<Widget>[
                                  const SizedBox(height: AppSpacing.sm),
                                  const LinearProgressIndicator(),
                                ],
                              ],
                            ),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          TextButton(
                            onPressed: () => Navigator.of(
                              context,
                            ).pushNamed(AppRoutes.about),
                            child: const Text('About this prototype'),
                          ),
                        ],
                      ),
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
