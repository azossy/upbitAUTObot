import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../services/api_service.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';

class NewsScreen extends ConsumerStatefulWidget {
  const NewsScreen({super.key});

  @override
  ConsumerState<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends ConsumerState<NewsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  List<Map<String, dynamic>> _coinNews = [];
  List<Map<String, dynamic>> _upbitNotices = [];
  bool _loadingCoin = true;
  bool _loadingUpbit = true;
  String? _errorCoin;
  String? _errorUpbit;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _fetchCoinNews();
    _fetchUpbitNotices();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _fetchCoinNews() async {
    setState(() {
      _loadingCoin = true;
      _errorCoin = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final list = await api.getCoinNews(limit: 40);
      if (mounted) {
        setState(() {
          _coinNews = list;
          _loadingCoin = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorCoin = getApiErrorMessage(e, fallback: '뉴스를 불러오지 못했습니다.');
          _loadingCoin = false;
        });
      }
    }
  }

  Future<void> _fetchUpbitNotices() async {
    setState(() {
      _loadingUpbit = true;
      _errorUpbit = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final list = await api.getUpbitNotices();
      if (mounted) {
        setState(() {
          _upbitNotices = list;
          _loadingUpbit = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorUpbit = getApiErrorMessage(e, fallback: '공지를 불러오지 못했습니다.');
          _loadingUpbit = false;
        });
      }
    }
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (_) {}
  }

  String _formatDate(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.month}/${dt.day} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.newsNoticeTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: '실시간 코인 뉴스'),
            Tab(text: '업비트 공지'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildCoinNewsTab(theme),
          _buildUpbitNoticesTab(theme),
        ],
      ),
    );
  }

  Widget _buildCoinNewsTab(ThemeData theme) {
    if (_loadingCoin && _coinNews.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorCoin != null && _coinNews.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.warning_amber_rounded, size: 48, color: theme.colorScheme.error),
              const SizedBox(height: 16),
              Text(_errorCoin!, textAlign: TextAlign.center, style: theme.textTheme.bodyLarge),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _fetchCoinNews,
                icon: const Icon(Icons.refresh),
                label: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }
    if (_coinNews.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.article_outlined, size: 56, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text('표시할 뉴스가 없습니다.', style: theme.textTheme.bodyLarge?.copyWith(color: Colors.grey.shade600)),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _fetchCoinNews,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal, vertical: 12),
        itemCount: _coinNews.length,
        itemBuilder: (context, i) {
          final item = _coinNews[i];
          final title = item['title'] as String? ?? '(제목 없음)';
          final url = item['url'] as String? ?? '';
          final source = item['source'] as String? ?? '';
          final publishedAt = item['published_at'] as String?;
          final snippet = item['body_snippet'] as String?;
          return Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: InkWell(
              onTap: () => _openUrl(url),
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (snippet != null && snippet.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        snippet,
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.75)),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        if (source.isNotEmpty)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.primaryContainer.withOpacity(0.6),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(source, style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.primary)),
                          ),
                        const SizedBox(width: 8),
                        Text(
                          _formatDate(publishedAt),
                          style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.6)),
                        ),
                        const Spacer(),
                        Icon(Icons.open_in_new, size: 16, color: theme.colorScheme.primary),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildUpbitNoticesTab(ThemeData theme) {
    if (_loadingUpbit && _upbitNotices.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorUpbit != null && _upbitNotices.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.warning_amber_rounded, size: 48, color: theme.colorScheme.error),
              const SizedBox(height: 16),
              Text(_errorUpbit!, textAlign: TextAlign.center, style: theme.textTheme.bodyLarge),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _fetchUpbitNotices,
                icon: const Icon(Icons.refresh),
                label: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }
    if (_upbitNotices.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.campaign_outlined, size: 56, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text('표시할 공지가 없습니다.', style: theme.textTheme.bodyLarge?.copyWith(color: Colors.grey.shade600)),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _fetchUpbitNotices,
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal, vertical: 12),
        itemCount: _upbitNotices.length,
        itemBuilder: (context, i) {
          final item = _upbitNotices[i];
          final title = item['title'] as String? ?? '업비트 공지';
          final url = item['url'] as String? ?? '';
          final source = item['source'] as String? ?? '업비트';
          final snippet = item['body_snippet'] as String?;
          return Card(
            margin: const EdgeInsets.only(bottom: 10),
            child: InkWell(
              onTap: () => _openUrl(url),
              borderRadius: BorderRadius.circular(AppTheme.radiusCard),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.campaign_outlined, size: 20, color: theme.colorScheme.primary),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            title,
                            style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Icon(Icons.open_in_new, size: 18, color: theme.colorScheme.primary),
                      ],
                    ),
                    if (snippet != null && snippet.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      Text(
                        snippet,
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.75)),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 6),
                    Text(
                      source,
                      style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.onSurface.withOpacity(0.6)),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
