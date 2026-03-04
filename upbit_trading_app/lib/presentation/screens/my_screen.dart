import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/api_service.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';
import '../../l10n/app_localizations.dart';
import '../../providers/locale_provider.dart';
import '../../constants/app_version.dart';

class MyScreen extends ConsumerStatefulWidget {
  const MyScreen({super.key});

  @override
  ConsumerState<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends ConsumerState<MyScreen> {
  Map<String, dynamic>? _profile;
  bool _loading = true;
  String? _error;
  bool _uploadingAvatar = false;
  late TextEditingController _nicknameController;

  @override
  void initState() {
    super.initState();
    _nicknameController = TextEditingController();
    _fetch();
  }

  @override
  void dispose() {
    _nicknameController.dispose();
    super.dispose();
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final data = await api.getProfile();
      if (mounted) {
        setState(() {
          _profile = data;
          _nicknameController.text = (data['nickname'] ?? '').toString();
          _loading = false;
        });
        final lang = data['preferred_language']?.toString();
        if (lang != null && lang.isNotEmpty && AppLocalizations.supportedLocales.contains(lang)) {
          ref.read(localeProvider.notifier).state = lang;
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = getApiErrorMessage(e, fallback: '프로필을 불러오지 못했습니다.');
          _loading = false;
        });
      }
    }
  }

  Future<void> _saveProfile() async {
    if (_profile == null) return;
    try {
      final api = ref.read(apiServiceProvider);
      await api.updateProfile(
        nickname: _nicknameController.text.trim().isEmpty ? null : _nicknameController.text.trim(),
      );
      if (mounted) {
        final l10n = ref.read(appLocalizationsProvider);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.saved), duration: const Duration(seconds: 3)),
        );
        _fetch();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(getApiErrorMessage(e, fallback: '저장에 실패했습니다.')),
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  Future<void> _onLanguageChanged(String? code) async {
    if (code == null || code.isEmpty) return;
    try {
      final api = ref.read(apiServiceProvider);
      await api.updateProfile(preferredLanguage: code);
      ref.read(localeProvider.notifier).state = code;
    } catch (_) {}
  }

  Future<void> _pickAndUploadAvatar(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final xFile = await picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      if (xFile == null || !mounted) return;
      setState(() => _uploadingAvatar = true);
      final api = ref.read(apiServiceProvider);
      final updated = await api.uploadAvatar(xFile);
      if (mounted) {
        setState(() {
          _profile = updated;
          _uploadingAvatar = false;
        });
        final l10n = ref.read(appLocalizationsProvider);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.saved), duration: const Duration(seconds: 3)),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _uploadingAvatar = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(getApiErrorMessage(e, fallback: '사진 업로드에 실패했습니다.')),
            duration: const Duration(seconds: 4),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(appLocalizationsProvider);
    final theme = Theme.of(context);

    if (_loading && _profile == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.myTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.myTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/'),
        ),
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
                    onTap: isAuthRequiredMessage(_error) ? () { ref.read(authStateProvider.notifier).logout(); context.go('/login'); } : null,
                    borderRadius: BorderRadius.circular(AppTheme.radiusCard),
                    child: Card(
                      color: theme.colorScheme.errorContainer.withOpacity(0.5),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.warning_amber_rounded, color: theme.colorScheme.error),
                                const SizedBox(width: 12),
                                Expanded(child: Text(_error!, style: TextStyle(color: theme.colorScheme.onSurface))),
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
              // 프로필
              Text(
                l10n.profile,
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                    child: Column(
                    children: [
                      Center(
                        child: Stack(
                          clipBehavior: Clip.none,
                          children: [
                            _buildAvatar(theme),
                            if (_uploadingAvatar)
                              Positioned.fill(
                                child: Container(
                                    decoration: const BoxDecoration(
                                    color: Colors.black45,
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Center(child: CircularProgressIndicator(color: Colors.white)),
                                ),
                              ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          FilledButton.tonalIcon(
                            onPressed: _uploadingAvatar ? null : () => _pickAndUploadAvatar(ImageSource.camera),
                            icon: const Icon(Icons.camera_alt, size: 20),
                            label: Text(l10n.photoCamera),
                          ),
                          const SizedBox(width: 12),
                          FilledButton.tonalIcon(
                            onPressed: _uploadingAvatar ? null : () => _pickAndUploadAvatar(ImageSource.gallery),
                            icon: const Icon(Icons.photo_library, size: 20),
                            label: Text(l10n.photoAlbum),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _nicknameController,
                        decoration: InputDecoration(
                          labelText: l10n.nickname,
                          border: const OutlineInputBorder(),
                          isDense: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        key: ValueKey(_profile?['email']),
                        initialValue: _profile?['email']?.toString() ?? '',
                        readOnly: true,
                        decoration: InputDecoration(
                          labelText: l10n.email,
                          border: const OutlineInputBorder(),
                          isDense: true,
                          filled: true,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _saveProfile,
                          icon: const Icon(Icons.save, size: 20),
                          label: Text(l10n.save),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              // 언어
              Text(
                l10n.language,
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: DropdownButtonFormField<String>(
                    value: AppLocalizations.supportedLocales.contains(ref.watch(localeProvider))
                        ? ref.watch(localeProvider)
                        : 'ko',
                    decoration: InputDecoration(
                      labelText: l10n.languageSelect,
                      border: const OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: AppLocalizations.supportedLocales.map((code) {
                      return DropdownMenuItem(
                        value: code,
                        child: Text(AppLocalizations.languageNames[code] ?? code),
                      );
                    }).toList(),
                    onChanged: _onLanguageChanged,
                  ),
                ),
              ),
              const SizedBox(height: 24),
              // 봇 설정 / 비밀번호 변경
              Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: const Icon(Icons.settings),
                      title: Text(l10n.botSettings),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.go('/settings'),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      leading: const Icon(Icons.lock_outline),
                      title: Text(l10n.passwordChange),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => context.go('/settings/password'),
                    ),
                    const Divider(height: 1),
                    ListTile(
                      leading: const Icon(Icons.logout),
                      title: Text(l10n.logout, style: TextStyle(color: theme.colorScheme.error)),
                      onTap: () {
                        ref.read(authStateProvider.notifier).logout();
                        context.go('/login');
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Center(
                child: Text(
                  '버전 $kAppVersion',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.5),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAvatar(ThemeData theme) {
    final api = ref.read(apiServiceProvider);
    final avatarUrl = _profile?['avatar_url']?.toString().trim();
    final fullUrl = avatarUrl != null && avatarUrl.isNotEmpty
        ? api.avatarFullUrl(avatarUrl)
        : '';
    if (fullUrl.isNotEmpty) {
      return CircleAvatar(
        radius: 44,
        backgroundColor: theme.colorScheme.primaryContainer,
        backgroundImage: NetworkImage(fullUrl),
        onBackgroundImageError: (_, __) {},
      );
    }
    final initial = (_profile?['nickname'] ?? '?').toString();
    return CircleAvatar(
      radius: 44,
      backgroundColor: theme.colorScheme.primaryContainer,
      child: Text(
        initial.isNotEmpty ? initial.substring(0, 1).toUpperCase() : '?',
        style: theme.textTheme.headlineMedium?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
