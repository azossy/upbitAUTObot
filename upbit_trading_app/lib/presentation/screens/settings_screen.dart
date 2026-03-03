import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../services/api_service.dart';
import '../../services/biometric_service.dart';
import '../../theme/app_theme.dart';
import '../../providers/locale_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  List<dynamic> _apiKeys = [];
  Map<String, dynamic>? _config;
  bool _loading = true;
  String? _error;
  bool? _serverConnected; // null=확인 중, true=연결됨, false=연결 끊김
  bool _biometricEnabled = false;
  bool _biometricAvailable = false;

  late final TextEditingController _telegramController;
  late final TextEditingController _stopLossController;
  late final TextEditingController _takeProfitController;
  late final TextEditingController _apiBaseUrlController;
  late double _investmentRatio;
  late int _maxPositions;

  @override
  void initState() {
    super.initState();
    _telegramController = TextEditingController();
    _stopLossController = TextEditingController(text: '2.5');
    _takeProfitController = TextEditingController(text: '7.0');
    _apiBaseUrlController = TextEditingController(text: ApiService.defaultBaseUrl);
    _investmentRatio = 0.5;
    _maxPositions = 7;
    _fetch();
  }

  @override
  void dispose() {
    _telegramController.dispose();
    _stopLossController.dispose();
    _takeProfitController.dispose();
    _apiBaseUrlController.dispose();
    super.dispose();
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final api = ref.read(apiServiceProvider);
    final prefs = await SharedPreferences.getInstance();
    final savedUrl = prefs.getString(ApiService.kApiBaseUrlKey)?.trim() ?? ApiService.defaultBaseUrl;
    if (mounted) setState(() => _apiBaseUrlController.text = savedUrl);
    final biometric = ref.read(biometricServiceProvider);
    final bioEnabled = await biometric.isBiometricEnabled();
    final bioAvailable = await biometric.canCheckBiometrics();
    if (mounted) setState(() {
      _biometricEnabled = bioEnabled;
      _biometricAvailable = bioAvailable;
    });
    final connected = await api.healthCheck();
    if (mounted) setState(() => _serverConnected = connected);
    List<dynamic> keys = [];
    Map<String, dynamic> config = {};
    try {
      keys = await api.getApiKeys();
    } catch (_) {}
    try {
      config = await api.getBotConfig();
    } catch (_) {}
    if (mounted) {
      setState(() {
        _apiKeys = keys;
        _config = config.isNotEmpty ? config : null;
        _investmentRatio =
            (config['max_investment_ratio'] ?? 0.5).toDouble();
        _maxPositions = config['max_positions'] ?? 7;
        _stopLossController.text =
            (config['stop_loss_pct'] ?? 2.5).toString();
        _takeProfitController.text =
            (config['take_profit_pct'] ?? 7.0).toString();
        _telegramController.text =
            config['telegram_chat_id']?.toString() ?? '';
        _error = keys.isEmpty && config.isEmpty ? '데이터 로드 실패' : null;
        _loading = false;
      });
    }
  }

  Future<void> _saveApiBaseUrl() async {
    final url = _apiBaseUrlController.text.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('주소를 입력하세요. http:// 또는 https:// 로 시작해야 합니다.')),
      );
      return;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('주소는 http:// 또는 https:// 로 시작해야 합니다.')),
      );
      return;
    }
    final ok = await ApiService.saveBaseUrl(url);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('저장에 실패했습니다.')),
      );
      return;
    }
    ref.read(apiServiceProvider).updateBaseUrl(url);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('API 서버 주소가 저장되었습니다.')),
      );
    }
  }

  Future<void> _showAddApiKeyDialog() async {
    final accessController = TextEditingController();
    final secretController = TextEditingController();
    final labelController = TextEditingController(text: '메인계정');

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('API 키 추가'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: accessController,
                decoration: const InputDecoration(
                  labelText: 'Access Key',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: secretController,
                decoration: const InputDecoration(
                  labelText: 'Secret Key',
                  border: OutlineInputBorder(),
                ),
                obscureText: true,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: labelController,
                decoration: const InputDecoration(
                  labelText: '라벨 (선택)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('추가'),
          ),
        ],
      ),
    );

    if (ok == true && mounted) {
      try {
        await ref.read(apiServiceProvider).addApiKey(
              accessController.text.trim(),
              secretController.text.trim(),
              label: labelController.text.trim().isEmpty
                  ? null
                  : labelController.text.trim(),
            );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('API 키가 등록되었습니다')),
          );
          _fetch();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(getApiErrorMessage(e, fallback: 'API 키 등록 실패'))),
          );
        }
      }
    }
  }

  Future<void> _deleteApiKey(int id, String label) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('API 키 삭제'),
        content: Text('$label API 키를 삭제하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('삭제'),
          ),
        ],
      ),
    );

    if (ok == true && mounted) {
      try {
        await ref.read(apiServiceProvider).deleteApiKey(id);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('API 키가 삭제되었습니다')),
          );
          _fetch();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(getApiErrorMessage(e, fallback: 'API 키 삭제 실패'))),
          );
        }
      }
    }
  }

  Future<void> _saveConfig() async {
    final stopLoss = double.tryParse(_stopLossController.text) ?? 2.5;
    final takeProfit = double.tryParse(_takeProfitController.text) ?? 7.0;
    try {
      await ref.read(apiServiceProvider).updateBotConfig(
            maxInvestmentRatio: _investmentRatio,
            maxPositions: _maxPositions,
            stopLossPct: stopLoss,
            takeProfitPct: takeProfit,
            telegramChatId: _telegramController.text.trim(),
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('설정이 저장되었습니다')),
        );
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(getApiErrorMessage(e, fallback: '설정 저장 실패'))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    if (_loading && _apiKeys.isEmpty && _config == null) {
      return Scaffold(
        appBar: AppBar(
          title: Text(l10n.settings),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.go('/'),
          ),
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.settings),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTheme.marginHorizontal),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 서버 연결 상태 (상용 프로그램 수준 UX)
            Card(
              child: ListTile(
                leading: Icon(
                  _serverConnected == true ? Icons.cloud_done : Icons.cloud_off,
                  color: _serverConnected == true
                      ? Colors.green
                      : Theme.of(context).colorScheme.error,
                  size: 28,
                ),
                title: const Text('서버 연결 상태'),
                subtitle: Text(
                  _serverConnected == null
                      ? '확인 중...'
                      : (_serverConnected == true ? '연결됨' : '연결 끊김'),
                  style: TextStyle(
                    color: _serverConnected == true
                        ? Colors.green
                        : (_serverConnected == false
                            ? Theme.of(context).colorScheme.error
                            : null),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                trailing: _serverConnected != null
                    ? TextButton(
                        onPressed: _fetch,
                        child: const Text('새로고침'),
                      )
                    : null,
              ),
            ),
            const SizedBox(height: 16),
            // API 서버 주소 (기획 5차 — 서버 URL 설정)
            Text(
              '연결',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _apiBaseUrlController,
                      decoration: const InputDecoration(
                        labelText: 'API 서버 주소',
                        hintText: 'http://127.0.0.1:8000',
                        border: OutlineInputBorder(),
                      ),
                      keyboardType: TextInputType.url,
                      onSubmitted: (_) => _saveApiBaseUrl(),
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: _saveApiBaseUrl,
                      child: const Text('저장'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // 비밀번호 변경 메뉴
            Text(
              '계정',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: Icon(Icons.lock_outline, color: Theme.of(context).colorScheme.primary),
                    title: const Text('비밀번호 변경'),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/settings/password'),
                  ),
                  if (_biometricAvailable) ...[
                    const Divider(height: 1),
                    SwitchListTile(
                      secondary: Icon(Icons.fingerprint, color: Theme.of(context).colorScheme.primary),
                      title: const Text('생체정보로 로그인'),
                      subtitle: const Text('다음 로그인부터 지문/얼굴 인식 사용'),
                      value: _biometricEnabled,
                      onChanged: (v) async {
                        final biometric = ref.read(biometricServiceProvider);
                        await biometric.setBiometricEnabled(v);
                        if (v) {
                          final token = ref.read(apiServiceProvider).getToken();
                          if (token != null) await biometric.saveToken(token);
                        }
                        if (mounted) setState(() => _biometricEnabled = v);
                      },
                    ),
                  ],
                ],
              ),
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
            Text(
              'API 키 관리',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            ..._apiKeys.map((k) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                      child: Icon(Icons.key, color: Theme.of(context).colorScheme.primary, size: 20),
                    ),
                    title: Text(k['label'] ?? '기본', style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text(k['masked_key'] ?? '••••••••', style: Theme.of(context).textTheme.bodySmall),
                    trailing: TextButton(
                      onPressed: () => _deleteApiKey(
                        k['id'] as int,
                        k['label'] ?? '기본',
                      ),
                      child: const Text('삭제'),
                    ),
                  ),
                )),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _showAddApiKeyDialog,
              icon: const Icon(Icons.add, size: 20),
              label: const Text('API 키 추가'),
            ),
            const SizedBox(height: 28),
            // 자동매매 책임 안내 (디스클레이머) — 매매 설정 위
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                '자동매매로 인한 손실은 사용자 책임이며, 서비스는 투자 결과에 대해 책임지지 않습니다.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
            ),
            Text(
              '매매 설정',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('투자 비율'),
                        Text(
                          '${(_investmentRatio * 100).toInt()}%',
                          style: TextStyle(color: Colors.grey[600]),
                        ),
                      ],
                    ),
                    Slider(
                      value: _investmentRatio,
                      onChanged: (v) => setState(() => _investmentRatio = v),
                      onChangeEnd: (_) => _saveConfig(),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('최대 포지션'),
                      trailing: DropdownButton<int>(
                        value: _maxPositions,
                        items: [3, 5, 7, 10].map((v) {
                          return DropdownMenuItem(
                            value: v,
                            child: Text('$v'),
                          );
                        }).toList(),
                        onChanged: (v) {
                          if (v != null) {
                            setState(() => _maxPositions = v);
                            _saveConfig();
                          }
                        },
                      ),
                    ),
                    ListTile(
                      title: const Text('손절 %'),
                      subtitle: const Text('0~100', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _stopLossController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          onSubmitted: (_) => _saveConfig(),
                        ),
                      ),
                    ),
                    ListTile(
                      title: const Text('익절 %'),
                      subtitle: const Text('0~100', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _takeProfitController,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          onSubmitted: (_) => _saveConfig(),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 28),
            Text(
              '텔레그램 연동',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: TextField(
                  controller: _telegramController,
                  decoration: const InputDecoration(
                    labelText: 'Chat ID',
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (_) => _saveConfig(),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _saveConfig,
                child: const Text('설정 저장'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
