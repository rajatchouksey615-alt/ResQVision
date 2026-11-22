import 'dart:async';

import 'package:flutter/material.dart';

import '../../../app/theme/app_spacing.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/app_empty_state.dart';
import '../../../core/widgets/app_error_state.dart';
import '../../../core/widgets/section_heading.dart';
import '../../authentication/data/models/authenticated_user.dart';
import '../data/candidate_review_repository.dart';

class CandidateReviewListScreen extends StatefulWidget {
  const CandidateReviewListScreen({
    super.key,
    required this.repository,
    required this.memberships,
    this.onDecision,
  });

  final CandidateReviewRepository repository;
  final List<OrganizationMembership> memberships;
  final Future<void> Function()? onDecision;

  @override
  State<CandidateReviewListScreen> createState() =>
      _CandidateReviewListScreenState();
}

class _CandidateReviewListScreenState extends State<CandidateReviewListScreen> {
  final List<ReviewCandidate> _candidates = <ReviewCandidate>[];
  int _totalCount = 0;
  int _nextOffset = 0;
  bool _hasMore = false;
  bool _isLoading = false;
  bool _isLoadingMore = false;
  String? _error;

  bool get _hasActivePoliceMembership => widget.memberships.any(
    (OrganizationMembership membership) =>
        membership.status == 'ACTIVE' &&
        membership.role == 'POLICE' &&
        membership.organizationKind == 'POLICE',
  );

  @override
  void initState() {
    super.initState();
    if (_hasActivePoliceMembership) unawaited(_load());
  }

  Future<void> _load({bool append = false}) async {
    if (_isLoading || _isLoadingMore) return;
    final int offset = append ? _nextOffset : 0;
    setState(() {
      if (append) {
        _isLoadingMore = true;
      } else {
        _isLoading = true;
        _candidates.clear();
      }
      _error = null;
    });
    try {
      final ReviewCandidatePage page = await widget.repository.loadPage(
        offset: offset,
      );
      if (!mounted) return;
      setState(() {
        if (append) {
          _candidates.addAll(page.candidates);
        } else {
          _candidates
            ..clear()
            ..addAll(page.candidates);
        }
        _totalCount = page.totalCount;
        _nextOffset = page.nextOffset;
        _hasMore = page.hasMore;
      });
    } on CandidateReviewException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _isLoadingMore = false;
        });
      }
    }
  }

  Future<void> _openCandidate(ReviewCandidate candidate) async {
    final bool? changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => CandidateReviewDetailScreen(
          repository: widget.repository,
          candidateId: candidate.id,
        ),
      ),
    );
    if (!mounted || changed != true) return;
    await _load();
    await widget.onDecision?.call();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Candidate and incident data refreshed.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_hasActivePoliceMembership) {
      return Scaffold(
        appBar: AppBar(title: const Text('Candidate review')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(AppSpacing.lg),
            child: AppEmptyState(
              title: 'Police membership required',
              message:
                  'Candidate review is available only in an active Police organization workspace.',
              icon: Icons.lock_outline,
            ),
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: <Widget>[
          const SectionHeading(
            title: 'Assigned candidate review',
            description:
                'Review candidates assigned to you by an authorized backend assigner. Evidence media and location details are not included.',
          ),
          const SizedBox(height: AppSpacing.md),
          if (_isLoading && _candidates.isEmpty)
            const AppCard(
              child: Column(
                children: <Widget>[
                  CircularProgressIndicator(),
                  SizedBox(height: AppSpacing.md),
                  Text('Loading assigned candidates…'),
                ],
              ),
            )
          else if (_error != null && _candidates.isEmpty)
            AppErrorState(
              title: 'Candidate queue unavailable',
              message: _error!,
              onRetry: _load,
            )
          else ...<Widget>[
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.only(bottom: AppSpacing.md),
                child: LinearProgressIndicator(),
              ),
            if (_error != null)
              AppCard(
                child: Row(
                  children: <Widget>[
                    Expanded(child: Text(_error!)),
                    TextButton(onPressed: _load, child: const Text('Retry')),
                  ],
                ),
              ),
            if (_candidates.isEmpty)
              const AppEmptyState(
                title: 'No assigned candidates',
                message:
                    'Candidates will appear here after an authorized assigner assigns them to your active Police membership.',
                icon: Icons.fact_check_outlined,
              )
            else ...<Widget>[
              AppCard(
                child: Text(
                  '${_candidates.length} shown · backend count $_totalCount in your assigned review scope',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              for (final ReviewCandidate candidate in _candidates) ...<Widget>[
                _CandidateCard(
                  candidate: candidate,
                  onTap: () => _openCandidate(candidate),
                ),
                const SizedBox(height: AppSpacing.sm),
              ],
              if (_hasMore)
                Center(
                  child: OutlinedButton.icon(
                    onPressed: _isLoadingMore
                        ? null
                        : () => _load(append: true),
                    icon: _isLoadingMore
                        ? const SizedBox.square(
                            dimension: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.expand_more),
                    label: Text(_isLoadingMore ? 'Loading…' : 'Load next page'),
                  ),
                ),
            ],
          ],
        ],
      ),
    );
  }
}

class _CandidateCard extends StatelessWidget {
  const _CandidateCard({required this.candidate, required this.onTap});

  final ReviewCandidate candidate;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.xs,
              children: <Widget>[
                Text(
                  'Candidate · ${candidate.id.substring(0, 8)}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                Chip(label: Text(_statusLabel(candidate.status))),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            Text('Created ${_dateLabel(candidate.createdAt)}'),
            const SizedBox(height: AppSpacing.sm),
            const Align(
              alignment: Alignment.centerRight,
              child: Text('Review details →'),
            ),
          ],
        ),
      ),
    ),
  );
}

class CandidateReviewDetailScreen extends StatefulWidget {
  const CandidateReviewDetailScreen({
    super.key,
    required this.repository,
    required this.candidateId,
  });

  final CandidateReviewRepository repository;
  final String candidateId;

  @override
  State<CandidateReviewDetailScreen> createState() =>
      _CandidateReviewDetailScreenState();
}

class _CandidateReviewDetailScreenState
    extends State<CandidateReviewDetailScreen> {
  late Future<ReviewCandidate> _detail;
  bool _isSubmitting = false;
  String? _actionError;
  String? _startCommandId;
  String? _decisionCommandId;
  String? _decisionKind;
  String? _decisionRationale;

  @override
  void initState() {
    super.initState();
    _detail = _load();
  }

  Future<ReviewCandidate> _load() =>
      widget.repository.loadDetail(widget.candidateId);

  Future<void> _startReview() async {
    await _performAction(() async {
      _startCommandId ??= widget.repository.createCommandId();
      await widget.repository.startReview(
        widget.candidateId,
        commandId: _startCommandId,
      );
      _startCommandId = null;
      if (mounted) {
        setState(() {
          _detail = _load();
        });
      }
    });
  }

  Future<void> _verify() async {
    final bool confirmed =
        await showDialog<bool>(
          context: context,
          builder: (BuildContext context) => AlertDialog(
            title: const Text('Verify this candidate?'),
            content: const Text(
              'Verification records the decision and creates one OPEN incident.',
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Verify'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;
    _decisionKind = 'VERIFIED';
    _decisionCommandId ??= widget.repository.createCommandId();
    await _performAction(() async {
      await widget.repository.verifyCandidate(
        widget.candidateId,
        commandId: _decisionCommandId,
      );
      _decisionCommandId = null;
      _decisionKind = null;
      if (mounted) Navigator.of(context).pop(true);
    });
  }

  Future<void> _reject() async {
    final String? retryRationale = _decisionKind == 'REJECTED'
        ? _decisionRationale
        : null;
    if (retryRationale != null) {
      final bool retry =
          await showDialog<bool>(
            context: context,
            builder: (BuildContext context) => AlertDialog(
              title: const Text('Retry rejection?'),
              content: Text(
                'Retry the same decision with the same rationale:\n\n$retryRationale',
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Retry rejection'),
                ),
              ],
            ),
          ) ??
          false;
      if (!retry || !mounted) return;
      await _submitRejection(retryRationale);
      return;
    }
    final String? rationale = await showDialog<String>(
      context: context,
      builder: (BuildContext context) => const _RejectionRationaleDialog(),
    );
    if (rationale == null || !mounted) return;
    _decisionKind = 'REJECTED';
    _decisionRationale = rationale;
    _decisionCommandId ??= widget.repository.createCommandId();
    await _submitRejection(rationale);
  }

  Future<void> _submitRejection(String rationale) async {
    await _performAction(() async {
      await widget.repository.rejectCandidate(
        widget.candidateId,
        rationale: rationale,
        commandId: _decisionCommandId,
      );
      _decisionCommandId = null;
      _decisionKind = null;
      _decisionRationale = null;
      if (mounted) Navigator.of(context).pop(true);
    });
  }

  Future<void> _performAction(Future<void> Function() action) async {
    setState(() {
      _isSubmitting = true;
      _actionError = null;
    });
    try {
      await action();
    } on CandidateReviewException catch (error) {
      if (mounted) {
        setState(() {
          _actionError = error.message;
          if (error.statusCode == 409) _detail = _load();
        });
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Candidate details')),
    body: FutureBuilder<ReviewCandidate>(
      future: _detail,
      builder: (BuildContext context, AsyncSnapshot<ReviewCandidate> snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                CircularProgressIndicator(),
                SizedBox(height: AppSpacing.md),
                Text('Loading assigned candidate…'),
              ],
            ),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          final Object? error = snapshot.error;
          return AppErrorState(
            title: 'Candidate details unavailable',
            message: error is CandidateReviewException
                ? error.message
                : 'Candidate details could not be loaded. Try again.',
            onRetry: () => setState(() => _detail = _load()),
          );
        }
        return _buildDetail(snapshot.data!);
      },
    ),
  );

  Widget _buildDetail(ReviewCandidate candidate) => ListView(
    padding: const EdgeInsets.all(AppSpacing.lg),
    children: <Widget>[
      SectionHeading(
        title: 'Candidate · ${candidate.id.substring(0, 8)}',
        description:
            'This view contains the backend-approved candidate summary only.',
      ),
      const SizedBox(height: AppSpacing.md),
      AppCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _DetailRow(label: 'Candidate ID', value: candidate.id),
            _DetailRow(label: 'Status', value: _statusLabel(candidate.status)),
            _DetailRow(
              label: 'Police organization',
              value: candidate.policeOrganizationId ?? 'Unavailable',
            ),
            _DetailRow(
              label: 'Created',
              value: _dateLabel(candidate.createdAt),
            ),
            _DetailRow(
              label: 'Last updated',
              value: _dateLabel(candidate.updatedAt),
            ),
          ],
        ),
      ),
      const SizedBox(height: AppSpacing.md),
      const AppCard(
        child: Text(
          'Evidence media and location information are not available in this review view.',
        ),
      ),
      if (_actionError != null) ...<Widget>[
        const SizedBox(height: AppSpacing.md),
        AppCard(child: Text(_actionError!)),
      ],
      const SizedBox(height: AppSpacing.lg),
      if (candidate.canStartReview)
        FilledButton.icon(
          onPressed: _isSubmitting ? null : _startReview,
          icon: const Icon(Icons.play_arrow),
          label: Text(_isSubmitting ? 'Starting…' : 'Start review'),
        )
      else if (candidate.canDecide) ...<Widget>[
        if (_decisionKind == null || _decisionKind == 'VERIFIED')
          FilledButton.icon(
            onPressed: _isSubmitting ? null : _verify,
            icon: const Icon(Icons.verified_outlined),
            label: Text(
              _isSubmitting
                  ? 'Saving…'
                  : _decisionKind == 'VERIFIED'
                  ? 'Retry verification'
                  : 'Verify candidate',
            ),
          ),
        if (_decisionKind == null || _decisionKind == 'REJECTED') ...<Widget>[
          const SizedBox(height: AppSpacing.sm),
          OutlinedButton.icon(
            onPressed: _isSubmitting ? null : _reject,
            icon: const Icon(Icons.cancel_outlined),
            label: Text(
              _decisionKind == 'REJECTED'
                  ? 'Retry rejection'
                  : 'Reject candidate',
            ),
          ),
        ],
      ] else
        const AppCard(
          child: Text(
            'This candidate has a final decision and cannot be changed.',
          ),
        ),
    ],
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(
          width: 132,
          child: Text(label, style: Theme.of(context).textTheme.bodySmall),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(child: SelectableText(value)),
      ],
    ),
  );
}

class _RejectionRationaleDialog extends StatefulWidget {
  const _RejectionRationaleDialog();

  @override
  State<_RejectionRationaleDialog> createState() =>
      _RejectionRationaleDialogState();
}

class _RejectionRationaleDialogState extends State<_RejectionRationaleDialog> {
  final TextEditingController _rationaleController = TextEditingController();

  @override
  void dispose() {
    _rationaleController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Reject candidate'),
    content: TextField(
      controller: _rationaleController,
      autofocus: true,
      minLines: 3,
      maxLines: 5,
      maxLength: 2000,
      decoration: const InputDecoration(
        labelText: 'Rationale',
        hintText: 'Explain the reason for rejection',
        border: OutlineInputBorder(),
      ),
    ),
    actions: <Widget>[
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () {
          final String rationale = _rationaleController.text.trim();
          if (rationale.isNotEmpty) Navigator.pop(context, rationale);
        },
        child: const Text('Reject'),
      ),
    ],
  );
}

String _statusLabel(String status) => status
    .split('_')
    .map(
      (String word) =>
          word.isEmpty ? word : '${word[0]}${word.substring(1).toLowerCase()}',
    )
    .join(' ');

String _dateLabel(DateTime dateTime) {
  final DateTime local = dateTime.toLocal();
  final String month = local.month.toString().padLeft(2, '0');
  final String day = local.day.toString().padLeft(2, '0');
  final String hour = local.hour.toString().padLeft(2, '0');
  final String minute = local.minute.toString().padLeft(2, '0');
  return '${local.year}-$month-$day · $hour:$minute';
}
