import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';

class TradesScreen extends ConsumerStatefulWidget {
  const TradesScreen({super.key});

  @override
  ConsumerState<TradesScreen> createState() => _TradesScreenState();
}

class _TradesScreenState extends ConsumerState<TradesScreen> {
  List<dynamic> _trades = [];
  bool _loading = true;
  String? _error;
  int _selectedDays = 30; // 7, 30, 90

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final trades = await api.getTrades(days: _selectedDays);
      if (mounted) {
        setState(() {
          _trades = trades;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = getApiErrorMessage(e, fallback: '데이터 로드 실패');
          _loading = false;
        });
      }
    }
  }

  String _formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return '-';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }

  String _sideToKr(String? side) {
    if (side == null) return '-';
    switch (side.toLowerCase()) {
      case 'bid':
      case 'buy':
        return '매수';
      case 'ask':
      case 'sell':
        return '매도';
      default:
        return side;
    }
  }

  Future<void> _exportCsv() async {
    try {
      final api = ref.read(apiServiceProvider);
      final csv = await api.getTradesExportCsv(days: _selectedDays);
      await Clipboard.setData(ClipboardData(text: csv));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('CSV가 클립보드에 복사되었습니다. 엑셀 등에 붙여넣기 하세요.')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(getApiErrorMessage(e, fallback: 'CSV 내보내기 실패'))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.navTrades),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: _exportCsv,
            tooltip: 'CSV 내보내기',
          ),
        ],
      ),
      body: _loading && _trades.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _fetch,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppTheme.marginHorizontal),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '기간',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                            color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                          ),
                    ),
                    const SizedBox(height: 8),
                    SegmentedButton<int>(
                      segments: const [
                        ButtonSegment(value: 7, label: Text('7일')),
                        ButtonSegment(value: 30, label: Text('30일')),
                        ButtonSegment(value: 90, label: Text('90일')),
                      ],
                      selected: {_selectedDays},
                      onSelectionChanged: (Set<int> v) {
                        if (v.isNotEmpty && v.first != _selectedDays) {
                          setState(() => _selectedDays = v.first);
                          _fetch();
                        }
                      },
                    ),
                    const SizedBox(height: 20),
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
                    if (_trades.isEmpty)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
                          child: Center(
                            child: Column(
                              children: [
                                Icon(Icons.receipt_long_outlined, size: 56, color: Colors.grey.shade400),
                                const SizedBox(height: 16),
                                Text('거래 내역이 없습니다', style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: Colors.grey.shade600)),
                              ],
                            ),
                          ),
                        ),
                      )
                    else
                      ..._trades.map((t) => _TradeTile(
                          coin: t['coin'] ?? '-',
                          side: _sideToKr(t['side']),
                          price: (t['price'] ?? 0).toDouble(),
                          qty: (t['quantity'] ?? 0).toDouble(),
                          date: _formatDate(t['created_at']),
                        )),
                  ],
                ),
              ),
            ),
    );
  }
}

class _TradeTile extends StatelessWidget {
  final String coin;
  final String side;
  final double price;
  final double qty;
  final String date;

  const _TradeTile({
    required this.coin,
    required this.side,
    required this.price,
    required this.qty,
    required this.date,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final amount = price * qty;
    final isBuy = side == '매수';
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        leading: CircleAvatar(
          radius: 20,
          backgroundColor: isBuy ? Colors.red.shade50 : Colors.blue.shade50,
          child: Icon(
            isBuy ? Icons.arrow_downward : Icons.arrow_upward,
            size: 20,
            color: isBuy ? Colors.red.shade700 : Colors.blue.shade700,
          ),
        ),
        title: Text('$coin $side', style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(date, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.7))),
        trailing: Text(
          amount >= 10000 ? '${(amount / 10000).toStringAsFixed(0)}만원' : amount.toStringAsFixed(0),
          style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
