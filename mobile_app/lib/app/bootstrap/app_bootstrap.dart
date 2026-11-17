import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import '../../core/config/app_config.dart';
import '../../core/errors/app_error.dart';
import '../../core/errors/app_exception.dart';
import '../../core/logging/app_logger.dart';
import '../../core/networking/api_client.dart';
import '../../core/security/flutter_token_storage.dart';
import '../../features/authentication/application/auth_session_controller.dart';
import '../../features/authentication/data/auth_repository.dart';
import '../app.dart';

Future<void> bootstrap({AppConfig Function()? loadConfiguration}) async {
  WidgetsFlutterBinding.ensureInitialized();
  final AppLogger logger = AppLogger(verbose: kDebugMode);
  AppConfig? config;
  AppError? startupError;
  AuthSessionController? sessionController;

  try {
    final AppConfig loadedConfig =
        (loadConfiguration ?? AppConfig.fromEnvironment)();
    config = loadedConfig;
    sessionController = AuthSessionController(
      repository: AuthRepository(apiClient: ApiClient(config: loadedConfig)),
      tokenStorage: FlutterTokenStorage(),
    );
    unawaited(sessionController.restoreSession());
    logger.info('app.startup.ready');
  } on AppException catch (error) {
    startupError = AppErrorMapper.fromException(error);
    logger.error('app.startup.configuration_failed', error: error);
  } catch (error) {
    startupError = AppErrorMapper.fromException(error);
    logger.error('app.startup.failed', error: error);
  }

  runApp(
    ResQVisionApp(
      config: config,
      startupError: startupError,
      sessionController: sessionController,
    ),
  );
}
