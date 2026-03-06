import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../services/api_service.dart';
import '../../services/auth_provider.dart';
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
  late final TextEditingController _takeProfitTier1Controller;
  late final TextEditingController _takeProfitTier2Controller;
  late final TextEditingController _takeProfitTier3Controller;
  late final TextEditingController _timeStopHoursController;
  late final TextEditingController _apiBaseUrlController;
  late double _investmentRatio;

  @override
  void initState() {
    super.initState();
    _telegramController = TextEditingController();
    _stopLossController = TextEditingController(text: '2.5');
    _takeProfitController = TextEditingController(text: '7.0');
    _takeProfitTier1Controller = TextEditingController(text: '5.0');
    _takeProfitTier2Controller = TextEditingController(text: '10.0');
    _takeProfitTier3Controller = TextEditingController(text: '15.0');
    _timeStopHoursController = TextEditingController(text: '12');
    _apiBaseUrlController = TextEditingController(text: ApiService.defaultBaseUrl);
    _investmentRatio = 0.5;
    _fetch();
  }

  @override
  void dispose() {
    _telegramController.dispose();
    _stopLossController.dispose();
    _takeProfitController.dispose();
    _takeProfitTier1Controller.dispose();
    _takeProfitTier2Controller.dispose();
    _takeProfitTier3Controller.dispose();
    _timeStopHoursController.dispose();
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
    final savedUrl = prefs.getString(kApiBaseUrlKey)?.trim() ?? ApiService.defaultBaseUrl;
    if (mounted) {
      setState(() => _apiBaseUrlController.text = savedUrl);
    }
    final biometric = ref.read(biometricServiceProvider);
    final bioEnabled = await biometric.isBiometricEnabled();
    final bioAvailable = await biometric.canCheckBiometrics();
    if (mounted) {
      setState(() {
        _biometricEnabled = bioEnabled;
        _biometricAvailable = bioAvailable;
      });
    }
    final connected = await api.healthCheck();
    if (mounted) {
      setState(() => _serverConnected = connected);
    }
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
        _stopLossController.text =
            (config['stop_loss_pct'] ?? 2.5).toString();
        _takeProfitController.text =
            (config['take_profit_pct'] ?? 7.0).toString();
        _takeProfitTier1Controller.text =
            (config['take_profit_tier1_pct'] ?? 5.0).toString();
        _takeProfitTier2Controller.text =
            (config['take_profit_tier2_pct'] ?? 10.0).toString();
        _takeProfitTier3Controller.text =
            (config['take_profit_tier3_pct'] ?? 15.0).toString();
        _timeStopHoursController.text =
            (config['time_stop_hours'] ?? 12).toString();
        _telegramController.text =
            config['telegram_chat_id']?.toString() ?? '';
        _error = keys.isEmpty && config.isEmpty ? '데이터 로드 실패' : null;
        _loading = false;
      });
    }
  }

  Future<void> _showServerAddressDialog() async {
    final controller = TextEditingController(text: _apiBaseUrlController.text.trim());
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('API 서버 주소 변경'),
        content: SingleChildScrollView(
          child: TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: 'API 서버 주소',
              hintText: 'https://example.com:8000',
              helperText: 'http:// 또는 https:// 로 시작해야 합니다.',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.url,
            autofocus: true,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('저장'),
          ),
        ],
      ),
    );
    if (ok == true && mounted) {
      _apiBaseUrlController.text = controller.text.trim();
      await _saveApiBaseUrl();
      if (mounted) setState(() {});
    }
  }

  Future<void> _saveApiBaseUrl() async {
    final url = _apiBaseUrlController.text.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('주소를 입력하세요. http:// 또는 https:// 로 시작해야 합니다.'),
          duration: Duration(seconds: 4),
        ),
      );
      return;
    }
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('주소는 http:// 또는 https:// 로 시작해야 합니다.'),
          duration: Duration(seconds: 4),
        ),
      );
      return;
    }
    final ok = await ApiService.saveBaseUrl(url);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('저장에 실패했습니다.'),
          duration: Duration(seconds: 4),
        ),
      );
      return;
    }
    ref.read(apiServiceProvider).updateBaseUrl(url);
    if (mounted) {
      setState(() {});
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('API 서버 주소가 저장되었습니다.'),
          duration: Duration(seconds: 3),
        ),
      );
    }
  }

  Future<void> _showAddApiKeyDialog() async {
    final isUpdate = _apiKeys.isNotEmpty;
    final accessController = TextEditingController();
    final secretController = TextEditingController();
    final labelController = TextEditingController(
      text: isUpdate && _apiKeys.isNotEmpty ? (_apiKeys.first['label'] ?? '메인계정').toString() : '메인계정',
    );
    bool obscureSecret = true;

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(isUpdate ? 'API 키 변경' : 'API 키 등록'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isUpdate
                      ? '기존 키가 새 키로 교체됩니다. Access Key와 Secret Key를 입력하세요.'
                      : '업비트 API 키는 1개만 등록할 수 있습니다. 봇이 주문 실행에 사용합니다.',
                  style: Theme.of(ctx).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 12),
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
                  decoration: InputDecoration(
                    labelText: 'Secret Key',
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(
                        obscureSecret ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      ),
                      onPressed: () => setDialogState(() => obscureSecret = !obscureSecret),
                      style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
                    ),
                  ),
                  obscureText: obscureSecret,
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
              child: Text(isUpdate ? '변경' : '등록'),
            ),
          ],
        ),
      ),
    );

    if (ok == true && mounted) {
      try {
        if (_apiKeys.isNotEmpty) {
          final first = _apiKeys.first;
          await ref.read(apiServiceProvider).deleteApiKey(first['id'] as int);
        }
        await ref.read(apiServiceProvider).addApiKey(
              accessController.text.trim(),
              secretController.text.trim(),
              label: labelController.text.trim().isEmpty
                  ? null
                  : labelController.text.trim(),
            );
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(_apiKeys.isEmpty ? 'API 키가 등록되었습니다.' : 'API 키가 변경되었습니다.'),
              duration: const Duration(seconds: 3),
            ),
          );
          _fetch();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(getApiErrorMessage(e, fallback: 'API 키 등록 실패')),
              duration: const Duration(seconds: 4),
            ),
          );
        }
      }
    }
  }

  Future<void> _showTelegramDialog() async {
    final controller = TextEditingController(text: _telegramController.text.trim());
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('텔레그램 Chat ID'),
        content: SingleChildScrollView(
          child: TextField(
            controller: controller,
            decoration: const InputDecoration(
              labelText: 'Chat ID',
              hintText: '숫자로 된 Chat ID 입력',
              helperText: '텔레그램 봇에게 /start 후 표시되는 Chat ID를 입력하세요.',
              border: OutlineInputBorder(),
            ),
            keyboardType: TextInputType.number,
            autofocus: true,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('취소'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('저장'),
          ),
        ],
      ),
    );
    if (ok == true && mounted) {
      _telegramController.text = controller.text.trim();
      await _saveConfig();
      if (mounted) setState(() {});
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
            const SnackBar(
              content: Text('API 키가 삭제되었습니다'),
              duration: Duration(seconds: 3),
            ),
          );
          _fetch();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(getApiErrorMessage(e, fallback: 'API 키 삭제 실패')),
              duration: const Duration(seconds: 4),
            ),
          );
        }
      }
    }
  }

  Future<void> _saveConfig() async {
    final stopLoss = double.tryParse(_stopLossController.text) ?? 2.5;
    final takeProfit = double.tryParse(_takeProfitController.text) ?? 7.0;
    final tier1 = double.tryParse(_takeProfitTier1Controller.text) ?? 5.0;
    final tier2 = double.tryParse(_takeProfitTier2Controller.text) ?? 10.0;
    final tier3 = double.tryParse(_takeProfitTier3Controller.text) ?? 15.0;
    final timeStopHours = int.tryParse(_timeStopHoursController.text) ?? 12;
    if (stopLoss < 0 || stopLoss > 100 || takeProfit < 0 || takeProfit > 100 ||
        tier1 < 0 || tier1 > 100 || tier2 < 0 || tier2 > 100 || tier3 < 0 || tier3 > 100) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('손절·익절 %는 0~100 사이로 입력하세요.'),
            duration: Duration(seconds: 4),
          ),
        );
      }
      return;
    }
    if (timeStopHours < 1 || timeStopHours > 168) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('시간 손절은 1~168(시간) 사이로 입력하세요.'),
            duration: Duration(seconds: 4),
          ),
        );
      }
      return;
    }
    try {
      await ref.read(apiServiceProvider).updateBotConfig(
            maxInvestmentRatio: _investmentRatio,
            stopLossPct: stopLoss,
            takeProfitPct: takeProfit,
            takeProfitTier1Pct: tier1,
            takeProfitTier2Pct: tier2,
            takeProfitTier3Pct: tier3,
            timeStopHours: timeStopHours,
            telegramChatId: _telegramController.text.trim(),
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('설정이 저장되었습니다'),
            duration: Duration(seconds: 3),
          ),
        );
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(getApiErrorMessage(e, fallback: '설정 저장 실패')),
            duration: const Duration(seconds: 4),
          ),
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
            onPressed: () => context.go('/my'),
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
          onPressed: () => context.go('/my'),
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
            // API 서버 주소 — 현재값 표시 + 변경 버튼으로 입력창 노출 방지
            Text(
              'API 서버 주소',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              '서버 주소가 바뀌면 변경 버튼을 눌러 새 주소를 입력하세요. http:// 또는 https:// 로 시작해야 합니다.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                title: Text(
                  _apiBaseUrlController.text.trim().isEmpty
                      ? '미설정'
                      : _apiBaseUrlController.text.trim(),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: _serverConnected != null
                    ? Text(
                        _serverConnected == true ? '연결됨' : '연결 끊김',
                        style: TextStyle(
                          fontSize: 12,
                          color: _serverConnected == true ? Colors.green : Theme.of(context).colorScheme.error,
                        ),
                      )
                    : null,
                trailing: FilledButton.tonal(
                  onPressed: _showServerAddressDialog,
                  child: const Text('변경'),
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
                    onTap: () => context.push('/my/settings/password'),
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
            // API 키 등록 (텔레그램 바로 위, API 서버 주소와 동일 UX)
            Text(
              'API 키 등록',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              '업비트 API 키를 등록하면 자동매매 봇이 주문을 실행할 수 있습니다. 1개만 등록 가능합니다.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                title: Text(
                  _apiKeys.isEmpty
                      ? '미등록'
                      : '${(_apiKeys.first['label'] ?? '기본').toString()} · ${(_apiKeys.first['masked_key'] ?? '••••••••').toString()}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: FilledButton.tonal(
                  onPressed: _showAddApiKeyDialog,
                  child: Text(_apiKeys.isEmpty ? '등록' : '변경'),
                ),
              ),
            ),
            const SizedBox(height: 20),
            // 텔레그램 연동 (안내 + 현재값 + 등록/변경)
            Text(
              '텔레그램 연동',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(
              '텔레그램 봇으로 매매 알림을 받을 수 있습니다. 봇에게 /start 후 표시되는 Chat ID를 입력하세요.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 8),
            Card(
              child: ListTile(
                title: Text(
                  _telegramController.text.trim().isEmpty ? '미등록' : _telegramController.text.trim(),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: FilledButton.tonal(
                  onPressed: _showTelegramDialog,
                  child: Text(_telegramController.text.trim().isEmpty ? '등록' : '변경'),
                ),
              ),
            ),
            const SizedBox(height: 20),
            if (_error != null) ...[
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: isAuthRequiredMessage(_error) ? () { ref.read(authStateProvider.notifier).logout(); context.go('/login'); } : null,
                  borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                  child: Card(
                    color: Theme.of(context).colorScheme.errorContainer.withOpacity(0.5),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.warning_amber_rounded, color: Theme.of(context).colorScheme.error, size: 22),
                              const SizedBox(width: 12),
                              Expanded(child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.onSurface))),
                            ],
                          ),
                          if (isAuthRequiredMessage(_error)) ...[
                            const SizedBox(height: 12),
                            FilledButton.icon(
                              onPressed: () { ref.read(authStateProvider.notifier).logout(); context.go('/login'); },
                              icon: const Icon(Icons.login, size: 18),
                              label: const Text('로그인 화면으로'),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            const SizedBox(height: 20),
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
                      title: const Text('익절 % (전량)'),
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
                    const Divider(),
                    ListTile(
                      title: const Text('분할 익절 1단계 %'),
                      subtitle: const Text('예: +5% 구간 일부 청산', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _takeProfitTier1Controller,
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
                      title: const Text('분할 익절 2단계 %'),
                      subtitle: const Text('예: +10% 구간', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _takeProfitTier2Controller,
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
                      title: const Text('분할 익절 3단계 %'),
                      subtitle: const Text('예: +15% 구간', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _takeProfitTier3Controller,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            isDense: true,
                          ),
                          onSubmitted: (_) => _saveConfig(),
                        ),
                      ),
                    ),
                    const Divider(),
                    ListTile(
                      title: const Text('시간 손절 (시간)'),
                      subtitle: const Text('진입 후 N시간 경과 시 조건 만족하면 청산 (1~168)', style: TextStyle(fontSize: 12)),
                      trailing: SizedBox(
                        width: 80,
                        child: TextField(
                          controller: _timeStopHoursController,
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
