import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../authentication/data/models/authenticated_user.dart';
import '../data/dashboard_repository.dart';

class DashboardController extends ChangeNotifier {
  DashboardController({
    required DashboardRepository repository,
    required this.user,
    required List<DashboardRole> roles,
    required DashboardRole? initialRole,
  }) : _repository = repository,
       roles = List<DashboardRole>.unmodifiable(roles),
       _selectedRole = initialRole;

  final DashboardRepository _repository;
  final AuthenticatedUser user;
  final List<DashboardRole> roles;

  DashboardRole? _selectedRole;
  String? _selectedOrganizationId;
  List<DashboardIncident> _incidents = <DashboardIncident>[];
  int _totalCount = 0;
  int _nextOffset = 0;
  bool _hasMore = false;
  bool _isPartial = false;
  bool _isLoading = false;
  bool _isRefreshing = false;
  bool _isLoadingMore = false;
  bool _workspaceUnavailable = false;
  String? _error;
  String? _pageError;
  int _generation = 0;

  DashboardRole? get selectedRole => _selectedRole;
  String? get selectedOrganizationId => _selectedOrganizationId;
  List<DashboardIncident> get incidents => List.unmodifiable(_incidents);
  int get totalCount => _totalCount;
  bool get hasMore => _hasMore;
  bool get isPartial => _isPartial;
  bool get isLoading => _isLoading;
  bool get isRefreshing => _isRefreshing;
  bool get isLoadingMore => _isLoadingMore;
  bool get workspaceUnavailable => _workspaceUnavailable;
  String? get error => _error;
  String? get pageError => _pageError;

  @override
  void dispose() {
    ++_generation;
    super.dispose();
  }

  List<OrganizationMembership> get organizationOptions {
    final DashboardRole? role = _selectedRole;
    if (role == null) return const <OrganizationMembership>[];
    return user.memberships
        .where((OrganizationMembership membership) {
          if (membership.status != 'ACTIVE') return false;
          if (role == DashboardRole.admin) {
            return membership.role == membership.organizationKind &&
                (membership.organizationKind == 'POLICE' ||
                    membership.organizationKind == 'HOSPITAL');
          }
          return membership.role == role.code &&
              membership.organizationKind == role.code;
        })
        .toList(growable: false);
  }

  bool get hasOrganizationSelector => organizationOptions.length > 1;

  Future<void> refresh() async {
    if (_isLoading || _isRefreshing || _isLoadingMore) return;
    final int generation = ++_generation;
    final bool preserveData = _incidents.isNotEmpty;
    _error = null;
    _pageError = null;
    _workspaceUnavailable = false;
    if (preserveData) {
      _isRefreshing = true;
    } else {
      _isLoading = true;
      _incidents = <DashboardIncident>[];
      _totalCount = 0;
      _nextOffset = 0;
      _hasMore = false;
      _isPartial = false;
    }
    notifyListeners();

    final DashboardRole? role = _selectedRole;
    if (role == null) {
      _workspaceUnavailable = true;
      _finishInitialLoad(generation);
      return;
    }
    final List<OrganizationMembership> options = organizationOptions;
    if (role != DashboardRole.admin && options.isEmpty) {
      _workspaceUnavailable = true;
      _finishInitialLoad(generation);
      return;
    }

    try {
      final DashboardPage page = await _repository.loadPage(
        role: role,
        activeMemberships: user.memberships,
        organizationId: _selectedOrganizationId,
      );
      if (generation != _generation) return;
      _incidents = page.incidents;
      _totalCount = page.totalCount;
      _nextOffset = page.nextOffset;
      _hasMore = page.hasMore;
      _isPartial = page.isPartial;
    } on DashboardDataException catch (error) {
      if (generation != _generation) return;
      if (preserveData) {
        _pageError =
            'Refresh failed. Showing the last loaded data. ${error.message}';
      } else {
        _error = error.message;
      }
    } catch (_) {
      if (generation != _generation) return;
      const String message = 'Dashboard data could not be loaded. Try again.';
      if (preserveData) {
        _pageError = 'Refresh failed. Showing the last loaded data. $message';
      } else {
        _error = message;
      }
    } finally {
      _finishInitialLoad(generation);
    }
  }

  Future<void> loadMore() async {
    final DashboardRole? role = _selectedRole;
    if (role == null ||
        !_hasMore ||
        _isLoading ||
        _isRefreshing ||
        _isLoadingMore) {
      return;
    }
    final int generation = _generation;
    _isLoadingMore = true;
    _pageError = null;
    notifyListeners();
    try {
      final DashboardPage page = await _repository.loadPage(
        role: role,
        activeMemberships: user.memberships,
        organizationId: _selectedOrganizationId,
        offset: _nextOffset,
      );
      if (generation != _generation) return;
      _incidents = <DashboardIncident>[..._incidents, ...page.incidents];
      _totalCount = page.totalCount;
      _nextOffset = page.nextOffset;
      _hasMore = page.hasMore;
      _isPartial = _isPartial || page.isPartial;
    } on DashboardDataException catch (error) {
      if (generation == _generation) _pageError = error.message;
    } catch (_) {
      if (generation == _generation) {
        _pageError = 'More dashboard data could not be loaded. Try again.';
      }
    } finally {
      if (generation == _generation) {
        _isLoadingMore = false;
        notifyListeners();
      }
    }
  }

  void selectRole(DashboardRole role) {
    if (!roles.contains(role) || role == _selectedRole) return;
    _selectedRole = role;
    _selectedOrganizationId = null;
    _resetForContextChange();
  }

  void selectOrganization(String? organizationId) {
    if (organizationId == _selectedOrganizationId) return;
    if (organizationId != null &&
        !organizationOptions.any(
          (OrganizationMembership membership) =>
              membership.organizationId == organizationId,
        )) {
      return;
    }
    _selectedOrganizationId = organizationId;
    _resetForContextChange();
  }

  void _resetForContextChange() {
    ++_generation;
    _incidents = <DashboardIncident>[];
    _totalCount = 0;
    _nextOffset = 0;
    _hasMore = false;
    _isPartial = false;
    _isLoading = false;
    _isRefreshing = false;
    _isLoadingMore = false;
    _workspaceUnavailable = false;
    _error = null;
    _pageError = null;
    notifyListeners();
    unawaited(refresh());
  }

  void _finishInitialLoad(int generation) {
    if (generation != _generation) return;
    _isLoading = false;
    _isRefreshing = false;
    notifyListeners();
  }
}
