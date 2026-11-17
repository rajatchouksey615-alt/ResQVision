import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import '../../core/config/app_config.dart';
import '../../core/errors/app_error.dart';
import '../../core/errors/app_exception.dart';
import '../../core/logging/app_logger.dart';
import '../app.dart';

Future<void> bootstrap({AppConfig Function()? loadConfiguration}) async {
  WidgetsFlutterBinding.ensureInitialized();
  final AppLogger logger = AppLogger(verbose: kDebugMode);
  AppConfig? config;
  AppError? startupError;

  try {
    config = (loadConfiguration ?? AppConfig.fromEnvironment)();
    logger.info('app.startup.ready');
  } on AppException catch (error) {
    startupError = AppErrorMapper.fromException(error);
    logger.error('app.startup.configuration_failed', error: error);
  } catch (error) {
    startupError = AppErrorMapper.fromException(error);
    logger.error('app.startup.failed', error: error);
  }

  runApp(ResQVisionApp(config: config, startupError: startupError));
}
