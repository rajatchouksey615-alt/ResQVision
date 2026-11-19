import 'package:flutter/foundation.dart';

import '../../authentication/data/models/authenticated_user.dart';
import '../../dashboard/data/dashboard_repository.dart';
import '../data/incident_repository.dart';

class IncidentListController extends ChangeNotifier {
  IncidentListController({
    required IncidentRepository repository,
    required this.role,
    required List<OrganizationMembership> memberships,
    required this.organizationId,
  }) : _repository = repository,
       memberships = List<OrganizationMembership>.unmodifiable(memberships);

  final IncidentRepository _repository;
  final DashboardRole role;
  final List<OrganizationMembership> memberships;
  final String? organizationId;

  final List<ManagedIncident> _incidents = <ManagedIncident>[];
  int _generation = 0;
  int _totalCount = 0;
  int _nextOffset = 0;
  bool _hasMore = false;
  bool _isLoading = false;
  bool _isLoadingMore = false;
  bool _isPartial = false;
  String? _selectedStatus;
  String? _error;
  String? _pageError;

  List<ManagedIncident> get incidents =>
      List<ManagedIncident>.unmodifiable(_incidents);
  int get totalCount => _totalCount;
  bool get hasMore => _hasMore;
  bool get isLoading => _isLoading;
  bool get isLoadingMore => _isLoadingMore;
  bool get isPartial => _isPartial;
  String? get selectedStatus => _selectedStatus;
  String? get error => _error;
  String? get pageError => _pageError;

  Future<void> refresh() async {
    final int generation = ++_generation;
    _isLoading = true;
    _isLoadingMore = false;
    _error = null;
    _pageError = null;
    _incidents.clear();
    _totalCount = 0;
    _nextOffset = 0;
    _hasMore = false;
    _isPartial = false;
    notifyListeners();
    try {
      final ManagedIncidentPage page = await _repository.loadPage(
        role: role,
        activeMemberships: memberships,
        organizationId: organizationId,
        status: _selectedStatus,
      );
      if (generation != _generation) return;
      _incidents.addAll(page.incidents);
      _totalCount = page.totalCount;
      _nextOffset = page.nextOffset;
      _hasMore = page.hasMore;
      _isPartial = page.isPartial;
    } on IncidentDataException catch (error) {
      if (generation == _generation) _error = error.message;
    } finally {
      if (generation == _generation) {
        _isLoading = false;
        notifyListeners();
      }
    }
  }

  Future<void> loadMore() async {
    if (!_hasMore || _isLoading || _isLoadingMore) return;
    final int generation = _generation;
    _isLoadingMore = true;
    _pageError = null;
    notifyListeners();
    try {
      final ManagedIncidentPage page = await _repository.loadPage(
        role: role,
        activeMemberships: memberships,
        organizationId: organizationId,
        status: _selectedStatus,
        offset: _nextOffset,
      );
      if (generation != _generation) return;
      _incidents.addAll(page.incidents);
      _totalCount = page.totalCount;
      _nextOffset = page.nextOffset;
      _hasMore = page.hasMore;
      _isPartial = _isPartial || page.isPartial;
    } on IncidentDataException catch (error) {
      if (generation == _generation) _pageError = error.message;
    } finally {
      if (generation == _generation) {
        _isLoadingMore = false;
        notifyListeners();
      }
    }
  }

  Future<void> setStatus(String? status) async {
    if (status == _selectedStatus) return;
    if (status != null &&
        !IncidentRepository.supportedStatuses.contains(status)) {
      throw ArgumentError.value(status, 'status');
    }
    _selectedStatus = status;
    await refresh();
  }
}
