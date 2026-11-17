import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:resqvision_mobile/core/logging/app_logger.dart';

void main() {
  test('logs structured event identifiers without exception messages', () {
    final List<AppLogRecord> records = <AppLogRecord>[];
    final AppLogger logger = AppLogger(verbose: true, sink: records.add);

    logger.error(
      'network.request.failed',
      error: _SensitiveException('access-token-private-value'),
    );

    final String recordJson = jsonEncode(records.single.toJson());
    expect(records.single.level, AppLogLevel.error);
    expect(records.single.event, 'network.request.failed');
    expect(records.single.errorType, '_SensitiveException');
    expect(recordJson, isNot(contains('access-token-private-value')));
  });

  test('suppresses debug events when verbose logging is disabled', () {
    final List<AppLogRecord> records = <AppLogRecord>[];
    final AppLogger logger = AppLogger(verbose: false, sink: records.add);

    logger.debug('app.startup.details');
    logger.info('app.startup.ready');

    expect(records.map((AppLogRecord record) => record.event), <String>[
      'app.startup.ready',
    ]);
  });
}

class _SensitiveException implements Exception {
  _SensitiveException(this.value);

  final String value;

  @override
  String toString() => value;
}
