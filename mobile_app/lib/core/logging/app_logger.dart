import 'dart:convert';
import 'dart:developer' as developer;

enum AppLogLevel {
  debug(500),
  info(800),
  warning(900),
  error(1000);

  const AppLogLevel(this.severity);

  final int severity;
}

class AppLogRecord {
  const AppLogRecord({
    required this.timestamp,
    required this.level,
    required this.event,
    this.errorType,
  });

  final DateTime timestamp;
  final AppLogLevel level;
  final String event;
  final String? errorType;

  Map<String, Object?> toJson() => <String, Object?>{
    'timestamp': timestamp.toUtc().toIso8601String(),
    'level': level.name,
    'event': event,
    if (errorType != null) 'errorType': errorType,
  };
}

typedef AppLogSink = void Function(AppLogRecord record);

class AppLogger {
  AppLogger({required this.verbose, AppLogSink? sink})
    : _sink = sink ?? _writeToDeveloperLog;

  final bool verbose;
  final AppLogSink _sink;

  static final RegExp _eventPattern = RegExp(
    r'^[a-z][a-z0-9]*(?:[._][a-z0-9]+)*$',
  );

  void debug(String event) {
    if (verbose) {
      _emit(AppLogLevel.debug, event);
    }
  }

  void info(String event) => _emit(AppLogLevel.info, event);

  void warning(String event, {Object? error}) =>
      _emit(AppLogLevel.warning, event, error: error);

  void error(String event, {Object? error}) =>
      _emit(AppLogLevel.error, event, error: error);

  void _emit(AppLogLevel level, String event, {Object? error}) {
    if (!_eventPattern.hasMatch(event)) {
      throw ArgumentError.value(event, 'event', 'Use a safe event identifier.');
    }
    _sink(
      AppLogRecord(
        timestamp: DateTime.now().toUtc(),
        level: level,
        event: event,
        errorType: error?.runtimeType.toString(),
      ),
    );
  }

  static void _writeToDeveloperLog(AppLogRecord record) {
    developer.log(
      jsonEncode(record.toJson()),
      name: 'resqvision',
      level: record.level.severity,
    );
  }
}
