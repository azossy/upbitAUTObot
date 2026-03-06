import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../services/api_service.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../utils/format.dart';
import '../../providers/locale_provider.dart';
import '../../utils/dashboard_messages.dart';
import '../widgets/pnl_chart.dart';
import '../widgets/pnl_history_chart.dart';

void _goToLogin(BuildContext context, WidgetRef ref) {
  ref.read(authStateProvider.notifier).logout();
  context.go('/login');
}

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

const List<String> _defaultTickerMarkets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-SOL'];

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  Map<String, dynamic>? _status;
  List<dynamic> _positions = [];
  List<Map<String, dynamic>> _pnlHistory = [];
  Map<String, dynamic>? _balance; // { krw, assets, error? }
  Map<String, dynamic>? _profile; // 프로필(avatar_url, nickname)
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

  List<String> get _tickerMarkets {
    final markets = Set<String>.from(_defaultTickerMarkets);
    for (final p in _positions) {
      final coin = (p['coin'] as String? ?? '').toUpperCase();
      if (coin.isNotEmpty) markets.add('KRW-$coin');
    }
    return markets.toList();
  }

  Future<void> _fetchTicker() async {
    if (!mounted) return;
    try {
      final api = ref.read(apiServiceProvider);
      final list = await api.getTicker(_tickerMarkets);
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
      final results = await Future.wait([
        api.getBotStatus(),
        api.getPositions(),
        api.getPnlHistory(days: 30).catchError((_) => <Map<String, dynamic>>[]),
        api.getBalance().catchError((_) => <String, dynamic>{}),
        api.getProfile().catchError((_) => <String, dynamic>{}),
      ]);
      final status = results[0] as Map<String, dynamic>;
      final positions = results[1] as List<dynamic>;
      final pnlHistory = results[2] as List<Map<String, dynamic>>;
      final balance = results[3] as Map<String, dynamic>?;
      final profileRaw = results[4];
      final profile = (profileRaw is Map && profileRaw.isNotEmpty) ? profileRaw as Map<String, dynamic> : null;
      if (mounted) {
        setState(() {
          _status = status;
          _positions = positions;
          _pnlHistory = pnlHistory;
          _balance = balance;
          _profile = profile;
          _botRunning = status['status'] == 'running';
          _loading = false;
        });
      }
      _fetchTicker();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = getApiErrorMessage(e, fallback: '데이터 로드 실패. 백엔드가 실행 중인지 확인하세요.');
          _loading = false;
        });
      }
    }
  }

  /// 포지션 코인별 현재 원화가치 합산 (봇운영보유고). ticker 시세 기준.
  double get _botAssetsKrw {
    double sum = 0.0;
    for (final p in _positions) {
      final coin = (p['coin'] as String? ?? '').toUpperCase();
      final qty = (p['quantity'] as num?)?.toDouble() ?? 0.0;
      if (coin.isEmpty || qty <= 0) continue;
      final market = 'KRW-$coin';
      num? price;
      for (final e in _tickerData) {
        if ((e['market'] as String?) == market) {
          price = (e['trade_price'] as num?)?.toDouble();
          break;
        }
      }
      sum += qty * (price ?? 0).toDouble();
    }
    return sum;
  }

  double get _cashKrw {
    if (_balance == null || _balance!['error'] != null) return 0.0;
    return ((_balance!['krw'] as num?) ?? 0).toDouble();
  }

  double get _totalAssetsKrw => _cashKrw + _botAssetsKrw;

  /// 월간 수익률(%): 최근 30일 pnl 합산 기준으로 근사
  double get _monthlyPnl {
    if (_pnlHistory.isEmpty) return 0.0;
    double sum = 0.0;
    final startKrw = (_status?['session_start_krw'] as num?)?.toDouble();
    if (startKrw == null || startKrw <= 0) return 0.0;
    for (final e in _pnlHistory) {
      final v = (e['pnl_krw'] as num?)?.toDouble() ?? (e['pnl'] as num?)?.toDouble() ?? 0.0;
      sum += v;
    }
    return (sum / startKrw) * 100;
  }

  Widget _buildTotalReturnChip(BuildContext context) {
    final krw = (_balance != null && _balance!['error'] == null) ? ((_balance!['krw'] as num?) ?? 0).toDouble() : 0.0;
    final startKrw = (_status?['session_start_krw'] as num?)?.toDouble();
    double pct = 0.0;
    if (startKrw != null && startKrw > 0) {
      pct = ((krw - startKrw) / startKrw) * 100;
    }
    final isPositive = pct >= 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: (isPositive ? Colors.green : Colors.red).withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)}%',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: isPositive ? Colors.green.shade700 : Colors.red.shade700,
        ),
      ),
    );
  }

  Future<void> _toggleBot() async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.startBot();
      if (mounted) {
        setState(() => _botRunning = true);
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(getApiErrorMessage(e, fallback: '봇 시작에 실패했습니다.')),
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  Future<void> _stopBot({bool afterSell = false}) async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.stopBot(afterSell: afterSell);
      if (mounted) {
        setState(() => _botRunning = false);
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(getApiErrorMessage(e, fallback: '봇 정지에 실패했습니다.')),
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  Widget _buildProfileLeading(BuildContext context) {
    final theme = Theme.of(context);
    final api = ref.read(apiServiceProvider);
    final avatarUrl = _profile?['avatar_url']?.toString().trim();
    final fullUrl = avatarUrl != null && avatarUrl.isNotEmpty ? api.avatarFullUrl(avatarUrl) : '';
    final nickname = (_profile?['nickname'] ?? ref.read(authStateProvider).user?['nickname'] ?? '') as String;
    return Padding(
      padding: const EdgeInsets.only(left: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (fullUrl.isNotEmpty)
            CircleAvatar(
              radius: 20,
              backgroundColor: theme.colorScheme.primaryContainer,
              backgroundImage: NetworkImage(fullUrl),
              onBackgroundImageError: (_, __) {},
            )
          else
            CircleAvatar(
              radius: 20,
              backgroundColor: theme.colorScheme.primaryContainer,
              child: Text(
                nickname.isNotEmpty ? nickname.substring(0, 1).toUpperCase() : '?',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              nickname.isNotEmpty ? nickname : '사용자',
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
                overflow: TextOverflow.ellipsis,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  String get _nickname => (_profile?['nickname'] ?? ref.read(authStateProvider).user?['nickname'] ?? '') as String;

  String _resolveDashboardMessage() {
    final hasError = _balance != null && _balance!['error'] != null;
    final errStr = hasError ? (_balance!['error'] as String? ?? '') : '';
    final hasApiKeyError = errStr.contains('등록') || errStr.contains('API 키를') || errStr.isEmpty && hasError;
    final dailyPnl = (_status?['daily_pnl'] as num?)?.toDouble();
    final weeklyPnl = (_status?['weekly_pnl'] as num?)?.toDouble();
    final type = DashboardMessages.resolveType(
      hasApiKeyError: hasApiKeyError,
      hasBalanceError: hasError,
      isFirstVisitToday: true,
      isReturnUser: false,
      dailyPnl: dailyPnl,
      weeklyPnl: weeklyPnl,
      hasPositions: _positions.isNotEmpty,
      botRunning: _botRunning,
      isNewUser: _profile == null && _balance == null,
    );
    return DashboardMessages.getMessage(type: type, nickname: _nickname);
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
        leading: Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.only(left: 4),
            child: _buildProfileLeading(context),
          ),
        ),
        leadingWidth: 160,
        centerTitle: true,
        title: Text(l10n.navDashboard),
        actions: [
          const SizedBox(width: 112),
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
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: isAuthRequiredMessage(_error)
                        ? () => _goToLogin(context, ref)
                        : null,
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    child: Card(
                      color: Theme.of(context).colorScheme.errorContainer.withOpacity(0.5),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.warning_amber_rounded, color: Theme.of(context).colorScheme.error),
                                const SizedBox(width: 12),
                                Expanded(child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onSurface))),
                              ],
                            ),
                            const SizedBox(height: 12),
                            if (isAuthRequiredMessage(_error))
                              FilledButton.icon(
                                onPressed: () => _goToLogin(context, ref),
                                icon: const Icon(Icons.login, size: 18),
                                label: const Text('로그인 화면으로'),
                              )
                            else
                              TextButton.icon(
                                onPressed: () { setState(() => _error = null); _fetch(); },
                                icon: const Icon(Icons.refresh, size: 18),
                                label: const Text('다시 시도'),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (_balance != null) ...[
                // 총보유자산 (상단, 우측 정렬)
                Align(
                  alignment: Alignment.centerRight,
                  child: Text(
                    '총보유자산',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Text(
                      '${formatKrw(_totalAssetsKrw.toInt())}원',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    if (_botRunning && _status != null) ...[
                      const SizedBox(width: 12),
                      _buildTotalReturnChip(context),
                    ],
                  ],
                ),
                const SizedBox(height: 12),
                // 현금보유고(원화잔고) | 봇운영보유고 (2분할, 숫자 우측 정렬)
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Align(
                                alignment: Alignment.centerRight,
                                child: Text(
                                  '현금보유고(원화잔고)',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                _balance!['error'] != null
                                    ? '0원'
                                    : '${formatKrw(_cashKrw.toInt())}원',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Align(
                                alignment: Alignment.centerRight,
                                child: Text(
                                  '봇운영보유고',
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.7),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                '${formatKrw(_botAssetsKrw.toInt())}원',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                // 안내 메시지 영역 (상황별 문구)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest.withOpacity(0.5),
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  ),
                  child: Text(
                    _resolveDashboardMessage(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withOpacity(0.85),
                      height: 1.35,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              // 수익 현황 (주요 시세보다 위로 이동)
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
              const SizedBox(height: 16),
              // 자동매매 책임 안내 (디스클레이머)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  '자동매매로 인한 손실은 사용자 책임이며, 서비스는 투자 결과에 대해 책임지지 않습니다.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                    height: 1.4,
                  ),
                ),
              ),
              // 봇 상태 및 시작/정지 버튼 (주요 시세보다 위에)
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
                      if (_botRunning)
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton.tonalIcon(
                                onPressed: () => _stopBot(afterSell: true),
                                icon: const Icon(Icons.sell_outlined, size: 18),
                                label: const Text('매각 후 봇정지'),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: FilledButton.icon(
                                onPressed: () => _stopBot(afterSell: false),
                                icon: const Icon(Icons.stop_rounded, size: 18),
                                label: const Text('현 상태 봇정지'),
                              ),
                            ),
                          ],
                        )
                      else
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: _toggleBot,
                            icon: const Icon(Icons.play_arrow_rounded, size: 20),
                            label: const Text('시작'),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              // 주요 시세 (봇 버튼 아래로 이동)
              Text(
                '주요 시세',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: _tickerData.isEmpty
                      ? Text(
                          '—',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6)),
                        )
                      : Column(
                          children: _tickerData.map((t) {
                            final market = t['market'] as String? ?? '-';
                            final symbol = market.replaceFirst('KRW-', '');
                            final price = (t['trade_price'] as num?)?.toDouble() ?? 0.0;
                            final rate = (t['signed_change_rate'] as num?)?.toDouble() ?? 0.0;
                            final change = t['change'] as String?;
                            final isRise = change == 'RISE';
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 6),
                              child: Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      _CoinLogo(symbol: symbol),
                                      const SizedBox(width: 8),
                                      Text(
                                        symbol,
                                        style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                                      ),
                                    ],
                                  ),
                                  Column(
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        '${formatKrw(price)}원',
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
              const SizedBox(height: 24),
              PnlChart(
                dailyPnl: (_status?['daily_pnl'] ?? 0).toDouble(),
                weeklyPnl: (_status?['weekly_pnl'] ?? 0).toDouble(),
                monthlyPnl: _monthlyPnl,
                cumulativePnl: (_status?['total_pnl'] as num?)?.toDouble() ?? 0.0,
              ),
              const SizedBox(height: 20),
              PnlHistoryChart(data: _pnlHistory),
            ],
          ),
        ),
      ),
      // 하단 네비게이션은 app.dart StatefulShellRoute에서 공통 표시
    );
  }
}

/// 주요 시세용 코인 로고 (작게, 연한 색)
class _CoinLogo extends StatelessWidget {
  final String symbol;

  const _CoinLogo({required this.symbol});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final label = symbol.length >= 2 ? symbol.substring(0, 2) : symbol;
    return CircleAvatar(
      radius: 12,
      backgroundColor: theme.colorScheme.primaryContainer.withOpacity(0.5),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: theme.colorScheme.primary.withOpacity(0.85),
          fontWeight: FontWeight.w600,
          fontSize: 9,
        ),
      ),
    );
  }
}

/// 비율(%) 표시용 카드 — 숫자는 가운데 정렬
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
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
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

