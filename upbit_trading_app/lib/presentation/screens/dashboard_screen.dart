import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';
import '../widgets/pnl_chart.dart';
import '../widgets/pnl_history_chart.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

const List<String> _defaultTickerMarkets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP'];

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  Map<String, dynamic>? _status;
  List<dynamic> _positions = [];
  List<Map<String, dynamic>> _pnlHistory = [];
  Map<String, dynamic>? _balance; // { krw, assets, error? }
  List<Map<String, dynamic>> _tickerData = [];
  bool _loading = true;
  String? _error;
  bool _botRunning = false;
  Timer? _tickerTimer;

  @override
  void initState() {
    super.initState();
    _fetch();
    _fetchTicker();
    _tickerTimer = Timer.periodic(const Duration(seconds: 60), (_) => _fetchTicker());
  }

  @override
  void dispose() {
    _tickerTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchTicker() async {
    if (!mounted) return;
    try {
      final api = ref.read(apiServiceProvider);
      final list = await api.getTicker(_defaultTickerMarkets);
      if (mounted) setState(() => _tickerData = list);
    } catch (_) {
      if (mounted) setState(() => _tickerData = []);
    }
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final status = await api.getBotStatus();
      final positions = await api.getPositions();
      List<Map<String, dynamic>> pnlHistory = [];
      try {
        pnlHistory = await api.getPnlHistory(days: 30);
      } catch (_) {}
      Map<String, dynamic>? balance;
      try {
        balance = await api.getBalance();
      } catch (_) {}
      try {
        _fetchTicker();
      } catch (_) {}
      if (mounted) {
        setState(() {
          _status = status;
          _positions = positions;
          _pnlHistory = pnlHistory;
          _balance = balance;
          _botRunning = status['status'] == 'running';
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = getApiErrorMessage(e, fallback: '데이터 로드 실패. 백엔드가 실행 중인지 확인하세요.');
          _loading = false;
        });
      }
    }
  }

  Future<void> _toggleBot() async {
    try {
      final api = ref.read(apiServiceProvider);
      if (_botRunning) {
        await api.stopBot();
      } else {
        await api.startBot();
      }
      _botRunning = !_botRunning;
      _fetch();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(getApiErrorMessage(e, fallback: '봇 제어에 실패했습니다.'))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _status == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('대시보드')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final l10n = ref.watch(appLocalizationsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.navDashboard),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: l10n.logout,
            onPressed: () {
              ref.read(authStateProvider.notifier).logout();
              context.go('/login');
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _fetch,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(AppTheme.marginHorizontal),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_error != null) ...[
                Card(
                  color: Theme.of(context).colorScheme.errorContainer.withOpacity(0.5),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.warning_amber_rounded, color: Theme.of(context).colorScheme.error),
                        const SizedBox(width: 12),
                        Expanded(child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onSurface))),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (_balance != null) ...[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Icon(Icons.account_balance_wallet_outlined, color: Theme.of(context).colorScheme.primary, size: 28),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('원화 잔고', style: Theme.of(context).textTheme.titleSmall?.copyWith(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7))),
                            const SizedBox(height: 4),
                            Text(
                              _balance!['error'] != null
                                  ? '—'
                                  : '${((_balance!['krw'] as num?) ?? 0).toStringAsFixed(0)}원',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: Theme.of(context).colorScheme.primary),
                            ),
                            if (_balance!['error'] != null && (_balance!['error'] as String).isNotEmpty)
                              Text('조회 실패', style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.error)),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              // 주요 시세 (실시간 ticker, 60초 주기 갱신)
              Text(
                '주요 시세',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: _tickerData.isEmpty
                      ? Text(
                          '—',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6)),
                        )
                      : Column(
                          children: _tickerData.map((t) {
                            final market = t['market'] as String? ?? '-';
                            final price = (t['trade_price'] as num?)?.toDouble() ?? 0.0;
                            final rate = (t['signed_change_rate'] as num?)?.toDouble() ?? 0.0;
                            final change = t['change'] as String?;
                            final isRise = change == 'RISE';
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    market.replaceFirst('KRW-', ''),
                                    style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        '${price.toStringAsFixed(0)}원',
                                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                                      ),
                                      Text(
                                        '${rate >= 0 ? '+' : ''}${(rate * 100).toStringAsFixed(2)}%',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: isRise ? Colors.green : (rate < 0 ? Colors.red : Theme.of(context).colorScheme.onSurface),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          }).toList(),
                        ),
                ),
              ),
              const SizedBox(height: 16),
              // 자동매매 책임 안내 (디스클레이머) — 봇 버튼 위
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  '자동매매로 인한 손실은 사용자 책임이며, 서비스는 투자 결과에 대해 책임지지 않습니다.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                  ),
                ),
              ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: _botRunning ? AppTheme.controlActive : Colors.grey,
                              shape: BoxShape.circle,
                              boxShadow: _botRunning ? [BoxShadow(color: AppTheme.primary.withOpacity(0.4), blurRadius: 6)] : null,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Text(
                            _botRunning ? '실행 중' : '정지됨',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          const Spacer(),
                          Chip(
                            label: Text(_status?['market_mode'] ?? '-', style: const TextStyle(fontSize: 12)),
                            padding: EdgeInsets.zero,
                            visualDensity: VisualDensity.compact,
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _toggleBot,
                          icon: Icon(_botRunning ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 20),
                          label: Text(_botRunning ? '정지' : '시작'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              PnlChart(
                dailyPnl: (_status?['daily_pnl'] ?? 0).toDouble(),
                weeklyPnl: (_status?['weekly_pnl'] ?? 0).toDouble(),
              ),
              const SizedBox(height: 20),
              PnlHistoryChart(data: _pnlHistory),
              const SizedBox(height: 20),
              Text(
                '수익 현황',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: _StatCard(title: '일일', value: '${_status?['daily_pnl'] ?? 0}%')),
                  const SizedBox(width: 12),
                  Expanded(child: _StatCard(title: '주간', value: '${_status?['weekly_pnl'] ?? 0}%')),
                  const SizedBox(width: 12),
                  Expanded(child: _StatCard(title: '승률', value: '${_status?['win_rate'] ?? 0}%')),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                '보유 포지션',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              if (_positions.isEmpty)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
                    child: Center(
                      child: Column(
                        children: [
                          Icon(Icons.account_balance_wallet_outlined, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 12),
                          Text('보유 포지션이 없습니다', style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
                    ),
                  ),
                )
              else
                ..._positions.map((p) => _PositionItem(
                      coin: p['coin'] ?? '-',
                      qty: (p['quantity'] ?? 0).toDouble(),
                      pnl: 0,
                    )),
            ],
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        onDestinationSelected: (i) {
          if (i == 1) context.go('/positions');
          if (i == 2) context.go('/trades');
          if (i == 3) context.go('/news');
          if (i == 4) context.go('/my');
        },
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home), label: ref.watch(appLocalizationsProvider).navDashboard),
          NavigationDestination(icon: const Icon(Icons.account_balance_wallet), label: ref.watch(appLocalizationsProvider).navPositions),
          NavigationDestination(icon: const Icon(Icons.list), label: ref.watch(appLocalizationsProvider).navTrades),
          NavigationDestination(icon: const Icon(Icons.newspaper), label: ref.watch(appLocalizationsProvider).navNews),
          NavigationDestination(icon: const Icon(Icons.person), label: ref.watch(appLocalizationsProvider).navMy),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;

  const _StatCard({required this.title, required this.value});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
        child: Column(
          children: [
            Text(title, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.6))),
            const SizedBox(height: 6),
            Text(value, style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold, color: theme.colorScheme.primary)),
          ],
        ),
      ),
    );
  }
}

class _PositionItem extends StatelessWidget {
  final String coin;
  final double qty;
  final double pnl;

  const _PositionItem({required this.coin, required this.qty, required this.pnl});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = pnl >= 0 ? Colors.red : Colors.blue;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        leading: CircleAvatar(
          radius: 20,
          backgroundColor: theme.colorScheme.primaryContainer,
          child: Text(coin.length > 2 ? coin.substring(0, 2).toUpperCase() : coin, style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary)),
        ),
        title: Text(coin, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('$qty'),
        trailing: Text(
          '${pnl >= 0 ? '+' : ''}$pnl%',
          style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 15),
        ),
      ),
    );
  }
}
