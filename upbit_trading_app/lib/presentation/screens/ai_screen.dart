import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';

/// AI 메뉴: 종목 지정 (오토/수동). 수동 시 업비트 원화 마켓 목록에서 최대 10종목 선택.
class AiScreen extends ConsumerStatefulWidget {
  const AiScreen({super.key});

  @override
  ConsumerState<AiScreen> createState() => _AiScreenState();
}

class _AiScreenState extends ConsumerState<AiScreen> {
  String _mode = 'auto'; // auto | manual
  List<String> _selectedMarkets = [];
  List<Map<String, dynamic>> _krwMarkets = [];
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  bool _loading = true;
  bool _saving = false;
  String? _error;

  static const int maxSelected = 10;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final api = ref.read(apiServiceProvider);
    try {
      final config = await api.getBotConfig();
      final markets = await api.getKrwMarkets();
      if (mounted) {
        setState(() {
          _mode = config['coin_select_mode']?.toString() == 'manual' ? 'manual' : 'auto';
          final list = config['selected_markets'];
          _selectedMarkets = list is List ? list.map((e) => e.toString()).where((s) => s.isNotEmpty).toList() : [];
          if (_selectedMarkets.length > maxSelected) {
            _selectedMarkets = _selectedMarkets.sublist(0, maxSelected);
          }
          _krwMarkets = markets;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '설정을 불러오지 못했습니다.';
          _loading = false;
        });
      }
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final api = ref.read(apiServiceProvider);
    try {
      await api.updateBotConfig(
        coinSelectMode: _mode,
        selectedMarkets: _mode == 'manual' ? _selectedMarkets : [],
      );
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('저장되었습니다.')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('저장 실패: ${e.toString()}')),
        );
      }
    }
  }

  List<Map<String, dynamic>> get _filteredMarkets {
    if (_searchQuery.trim().isEmpty) return _krwMarkets;
    final q = _searchQuery.trim().toLowerCase();
    return _krwMarkets.where((m) {
      final market = (m['market'] as String? ?? '').toLowerCase();
      final korean = (m['korean_name'] as String? ?? '').toLowerCase();
      final english = (m['english_name'] as String? ?? '').toLowerCase();
      return market.contains(q) || korean.contains(q) || english.contains(q);
    }).toList();
  }

  void _toggleMarket(String market) {
    if (_selectedMarkets.contains(market)) {
      setState(() => _selectedMarkets = _selectedMarkets.where((m) => m != market).toList());
    } else if (_selectedMarkets.length < maxSelected) {
      setState(() => _selectedMarkets = [..._selectedMarkets, market]);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.aiCoinSelectTitle),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(_error!, style: theme.textTheme.bodyLarge),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _load,
                        icon: const Icon(Icons.refresh),
                        label: const Text('다시 시도'),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal, vertical: 16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.aiModeHint,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.7),
                        ),
                      ),
                      const SizedBox(height: 16),
                      SegmentedButton<String>(
                        segments: [
                          ButtonSegment(value: 'auto', label: Text(l10n.aiModeAuto)),
                          ButtonSegment(value: 'manual', label: Text(l10n.aiModeManual)),
                        ],
                        selected: {_mode},
                        onSelectionChanged: (Set<String> sel) {
                          setState(() => _mode = sel.first);
                        },
                      ),
                      const SizedBox(height: 24),
                      if (_mode == 'manual') ...[
                        Text(
                          l10n.aiSelectedCount,
                          style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _selectedMarkets.map((m) {
                            String label = m;
                            for (final x in _krwMarkets) {
                              if (x['market'] == m) {
                                label = x['korean_name'] as String? ?? m;
                                break;
                              }
                            }
                            return Chip(
                              label: Text(label),
                              onDeleted: () => _toggleMarket(m),
                            );
                          }).toList(),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _searchController,
                          decoration: const InputDecoration(
                            labelText: '종목 검색',
                            hintText: '코드 또는 한글명 입력',
                            prefixIcon: Icon(Icons.search),
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (v) => setState(() => _searchQuery = v),
                        ),
                        const SizedBox(height: 12),
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxHeight: 320),
                          child: ListView.builder(
                            shrinkWrap: true,
                            itemCount: _filteredMarkets.length,
                            itemBuilder: (context, i) {
                              final m = _filteredMarkets[i];
                              final market = m['market'] as String? ?? '';
                              final korean = m['korean_name'] as String? ?? '';
                              final isSelected = _selectedMarkets.contains(market);
                              final canAdd = _selectedMarkets.length < maxSelected;
                              return ListTile(
                                title: Text(korean.isNotEmpty ? '$korean ($market)' : market),
                                trailing: isSelected
                                    ? const Icon(Icons.check_circle, color: Colors.green)
                                    : canAdd
                                        ? IconButton(
                                            icon: const Icon(Icons.add_circle_outline),
                                            onPressed: () => _toggleMarket(market),
                                          )
                                        : const SizedBox.shrink(),
                                onTap: () => _toggleMarket(market),
                              );
                            },
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: _saving ? null : _save,
                          child: _saving
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Text('저장'),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }
}
