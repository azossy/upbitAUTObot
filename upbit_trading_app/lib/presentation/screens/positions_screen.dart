import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';

class PositionsScreen extends ConsumerStatefulWidget {
  const PositionsScreen({super.key});

  @override
  ConsumerState<PositionsScreen> createState() => _PositionsScreenState();
}

const List<String> _defaultTickerMarkets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP'];

class _PositionsScreenState extends ConsumerState<PositionsScreen> {
  List<dynamic> _positions = [];
  List<Map<String, dynamic>> _tickerData = [];
  bool _loading = true;
  String? _error;
  Timer? _tickerTimer;

  @override
  void initState() {
    super.initState();
    _fetch();
    _tickerTimer = Timer.periodic(const Duration(seconds: 60), (_) => _fetchTicker());
  }

  @override
  void dispose() {
    _tickerTimer?.cancel();
    super.dispose();
  }

  List<String> _getTickerMarkets() {
    if (_positions.isEmpty) return _defaultTickerMarkets;
    final markets = _positions
        .map((p) => 'KRW-${(p['coin'] ?? '').toString().toUpperCase()}')
        .where((m) => m != 'KRW-')
        .toSet()
        .toList();
    return markets.isEmpty ? _defaultTickerMarkets : markets;
  }

  Future<void> _fetchTicker() async {
    if (!mounted) return;
    try {
      final api = ref.read(apiServiceProvider);
      final list = await api.getTicker(_getTickerMarkets());
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
      final positions = await api.getPositions();
      if (mounted) {
        setState(() {
          _positions = positions;
          _loading = false;
        });
        _fetchTicker();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '데이터 로드 실패';
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.navPositions),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
      ),
      body: _loading && _positions.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _fetch,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppTheme.marginHorizontal),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 주요 시세 (보유 마켓 또는 기본 마켓, 60초 주기)
                    Text(
                      '현재 시세',
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
                                        Text(market.replaceFirst('KRW-', ''), style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.end,
                                          children: [
                                            Text('${price.toStringAsFixed(0)}원', style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500)),
                                            Text(
                                              '${rate >= 0 ? '+' : ''}${(rate * 100).toStringAsFixed(2)}%',
                                              style: TextStyle(fontSize: 12, color: isRise ? Colors.green : (rate < 0 ? Colors.red : Theme.of(context).colorScheme.onSurface)),
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
                    if (_error != null) ...[
                      Card(
                        color: Theme.of(context).colorScheme.errorContainer.withOpacity(0.5),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            children: [
                              Icon(Icons.warning_amber_rounded, color: Theme.of(context).colorScheme.error, size: 22),
                              const SizedBox(width: 12),
                              Expanded(child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onSurface))),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],
                    if (_positions.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
                          child: Center(
                            child: Column(
                              children: [
                                Icon(Icons.account_balance_wallet_outlined, size: 56, color: Colors.grey.shade400),
                                const SizedBox(height: 16),
                                Text('보유 포지션이 없습니다', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.grey.shade600)),
                              ],
                            ),
                          ),
                        ),
                      )
                    else
                      ..._positions.map((p) => _PositionTile(
                          coin: p['coin'] ?? '-',
                          qty: (p['quantity'] ?? 0).toDouble(),
                          avgPrice: (p['avg_price'] ?? 0).toDouble(),
                        )),
                  ],
                ),
              ),
            ),
    );
  }
}

class _PositionTile extends StatelessWidget {
  final String coin;
  final double qty;
  final double avgPrice;

  const _PositionTile({
    required this.coin,
    required this.qty,
    required this.avgPrice,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        leading: CircleAvatar(
          radius: 22,
          backgroundColor: theme.colorScheme.primaryContainer,
          child: Text(
            coin.length > 2 ? coin.substring(0, 2).toUpperCase() : coin,
            style: theme.textTheme.labelLarge?.copyWith(color: theme.colorScheme.primary, fontWeight: FontWeight.w600),
          ),
        ),
        title: Text(coin, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '$qty · 평균 ${avgPrice >= 10000 ? "${(avgPrice / 10000).toStringAsFixed(0)}만원" : avgPrice.toStringAsFixed(0)}',
          style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.7)),
        ),
        trailing: avgPrice > 0
            ? Text('-', style: theme.textTheme.titleSmall?.copyWith(color: Colors.grey, fontWeight: FontWeight.w500))
            : null,
      ),
    );
  }
}
