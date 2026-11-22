import 'dart:convert';
import 'dart:math';

import '../../../core/errors/app_exception.dart';
import '../../../core/networking/api_request.dart';
import '../../../core/networking/authenticated_api_client.dart';

class CandidateReviewException implements Exception {
  const CandidateReviewException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ReviewCandidate {
  const ReviewCandidate({
    required this.id,
    required this.policeOrganizationId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String? policeOrganizationId;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get canStartReview => status == 'RECEIVED';
  bool get canDecide => status == 'UNDER_REVIEW';
}

class ReviewCandidatePage {
  const ReviewCandidatePage({
    required this.candidates,
    required this.totalCount,
    required this.nextOffset,
    required this.hasMore,
  });

  final List<ReviewCandidate> candidates;
  final int totalCount;
  final int nextOffset;
  final bool hasMore;
}

/// Uses only the summary fields authorized by the candidate API.
class CandidateReviewRepository {
  CandidateReviewRepository({required AuthenticatedApiClient apiClient})
    : _apiClient = apiClient;

  final AuthenticatedApiClient _apiClient;
  static const int pageSize = 25;
  static const Set<String> supportedStatuses = <String>{
    'RECEIVED',
    'UNDER_REVIEW',
    'VERIFIED',
    'REJECTED',
  };

  String createCommandId() => _newCommandId();

  Future<ReviewCandidatePage> loadPage({int offset = 0}) async {
    if (offset < 0) throw ArgumentError.value(offset, 'offset');
    final ApiResponse response = await _request(
      'GET',
      'candidates/?limit=$pageSize&offset=$offset',
      requestName: 'candidate list',
    );
    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'candidate page',
    );
    final int totalCount = _requiredInt(payload, 'count', 'candidate page');
    final Object? rows = payload['results'];
    if (rows is! List<Object?>) {
      throw const CandidateReviewException(
        'The candidate response did not match the expected format.',
      );
    }
    final String? next = _nullableString(payload, 'next', 'candidate page');
    return ReviewCandidatePage(
      candidates: List<ReviewCandidate>.unmodifiable(
        rows.map((Object? row) => _parseCandidate(row, 'candidate')),
      ),
      totalCount: totalCount,
      nextOffset: next == null ? offset : _offsetFromNext(next, offset),
      hasMore: next != null,
    );
  }

  Future<ReviewCandidate> loadDetail(String candidateId) async {
    _validateUuid(candidateId, 'candidateId');
    final ApiResponse response = await _request(
      'GET',
      'candidates/$candidateId/',
      requestName: 'candidate detail',
    );
    final ReviewCandidate candidate = _parseCandidate(
      _decodeObject(response.body, 'candidate'),
      'candidate',
    );
    if (candidate.id != candidateId) {
      throw const CandidateReviewException(
        'The candidate response did not match the requested record.',
      );
    }
    return candidate;
  }

  Future<void> startReview(String candidateId, {String? commandId}) async {
    final Map<String, Object?> data = await _command(
      candidateId: candidateId,
      action: 'review',
      body: <String, Object?>{'command_id': commandId ?? _newCommandId()},
      resource: 'candidate',
    );
    if (_parseCandidate(data, 'candidate').status != 'UNDER_REVIEW') {
      throw const CandidateReviewException(
        'The candidate did not enter review as expected.',
      );
    }
  }

  Future<void> verifyCandidate(
    String candidateId, {
    String? rationale,
    String? commandId,
  }) async {
    final Map<String, Object?> body = <String, Object?>{
      'command_id': commandId ?? _newCommandId(),
      if (rationale != null && rationale.trim().isNotEmpty)
        'rationale': rationale.trim(),
    };
    final Map<String, Object?> data = await _command(
      candidateId: candidateId,
      action: 'verify',
      body: body,
      resource: 'incident',
    );
    if (_requiredString(data, 'status', 'incident') != 'OPEN') {
      throw const CandidateReviewException(
        'Verification did not return an OPEN incident.',
      );
    }
    _requiredUuid(data, 'id', 'incident');
  }

  Future<void> rejectCandidate(
    String candidateId, {
    required String rationale,
    String? commandId,
  }) async {
    final String normalizedRationale = rationale.trim();
    if (normalizedRationale.isEmpty) {
      throw const CandidateReviewException(
        'A rejection rationale is required.',
      );
    }
    final Map<String, Object?> data = await _command(
      candidateId: candidateId,
      action: 'reject',
      body: <String, Object?>{
        'command_id': commandId ?? _newCommandId(),
        'rationale': normalizedRationale,
      },
      resource: 'candidate',
    );
    if (_parseCandidate(data, 'candidate').status != 'REJECTED') {
      throw const CandidateReviewException(
        'The candidate was not rejected as expected.',
      );
    }
  }

  Future<Map<String, Object?>> _command({
    required String candidateId,
    required String action,
    required Map<String, Object?> body,
    required String resource,
  }) async {
    _validateUuid(candidateId, 'candidateId');
    final ApiResponse response = await _request(
      'POST',
      'candidates/$candidateId/$action/',
      requestName: 'candidate $action',
      jsonBody: body,
    );
    final Map<String, Object?> payload = _decodeObject(
      response.body,
      'candidate command',
    );
    if (payload['replayed'] is! bool) {
      throw const CandidateReviewException(
        'The candidate command response did not match the expected format.',
      );
    }
    return _asObject(payload['data'], resource);
  }

  Future<ApiResponse> _request(
    String method,
    String path, {
    required String requestName,
    Object? jsonBody,
  }) async {
    try {
      final ApiResponse response = await _apiClient.request(
        method,
        path,
        jsonBody: jsonBody,
      );
      if (response.statusCode == 200) return response;
      final int status = response.statusCode;
      throw CandidateReviewException(switch (status) {
        400 => 'The candidate request is invalid. Check the supplied details.',
        401 => 'Your session is no longer authorized. Sign in again.',
        403 => 'You do not have permission to review this candidate.',
        404 => 'This candidate is unavailable in your assigned review scope.',
        409 =>
          'The candidate changed while you were reviewing it. Refresh and try again.',
        429 => 'Candidate review is rate limited. Try again shortly.',
        >= 500 => 'Candidate review is temporarily unavailable. Try again.',
        _ => 'The $requestName could not be completed.',
      }, statusCode: status);
    } on AppException catch (error) {
      throw CandidateReviewException(error.message);
    }
  }

  ReviewCandidate _parseCandidate(Object? value, String resource) {
    final Map<String, Object?> raw = _asObject(value, resource);
    final String status = _requiredString(raw, 'status', resource);
    if (!supportedStatuses.contains(status)) {
      throw CandidateReviewException(
        'The $resource response contained an unsupported status.',
      );
    }
    final Object? organizationId = raw['police_organization_id'];
    return ReviewCandidate(
      id: _requiredUuid(raw, 'id', resource),
      policeOrganizationId: organizationId == null
          ? null
          : _validateUuid(organizationId, '$resource organization'),
      status: status,
      createdAt: _requiredDate(raw, 'created_at', resource),
      updatedAt: _requiredDate(raw, 'updated_at', resource),
    );
  }

  Map<String, Object?> _decodeObject(String body, String resource) {
    try {
      return _asObject(jsonDecode(body), resource);
    } on FormatException {
      throw CandidateReviewException(
        'The $resource response did not match the expected format.',
      );
    }
  }

  Map<String, Object?> _asObject(Object? value, String resource) {
    if (value is Map<String, dynamic>) return value;
    throw CandidateReviewException(
      'The $resource response did not match the expected format.',
    );
  }

  String _requiredString(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final Object? field = value[key];
    if (field is String && field.isNotEmpty) return field;
    throw CandidateReviewException(
      'The $resource response did not match the expected format.',
    );
  }

  String _requiredUuid(
    Map<String, Object?> value,
    String key,
    String resource,
  ) => _validateUuid(_requiredString(value, key, resource), '$resource $key');

  String _validateUuid(Object? value, String fieldName) {
    const String pattern =
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';
    if (value is String && RegExp(pattern).hasMatch(value)) return value;
    throw CandidateReviewException('$fieldName is invalid.');
  }

  int _requiredInt(Map<String, Object?> value, String key, String resource) {
    final Object? field = value[key];
    if (field is int && field >= 0) return field;
    throw CandidateReviewException(
      'The $resource response did not match the expected format.',
    );
  }

  String? _nullableString(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final Object? field = value[key];
    if (field == null || field is String) return field as String?;
    throw CandidateReviewException(
      'The $resource response did not match the expected format.',
    );
  }

  DateTime _requiredDate(
    Map<String, Object?> value,
    String key,
    String resource,
  ) {
    final String raw = _requiredString(value, key, resource);
    final DateTime? parsed = DateTime.tryParse(raw);
    if (parsed != null) return parsed;
    throw CandidateReviewException(
      'The $resource response did not match the expected format.',
    );
  }

  int _offsetFromNext(String next, int currentOffset) {
    final Uri? uri = Uri.tryParse(next);
    final int? nextOffset = int.tryParse(uri?.queryParameters['offset'] ?? '');
    if (nextOffset == null || nextOffset <= currentOffset) {
      throw const CandidateReviewException(
        'The candidate page did not contain a valid next offset.',
      );
    }
    return nextOffset;
  }

  String _newCommandId() {
    final List<int> bytes = List<int>.generate(
      16,
      (_) => Random.secure().nextInt(256),
    );
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    final String hex = bytes
        .map((int byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join();
    return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
  }
}
