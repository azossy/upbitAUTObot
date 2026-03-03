import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import '../../services/auth_provider.dart';
import '../../services/biometric_service.dart';
import '../../theme/app_theme.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  String? _error;
  bool _showBiometricButton = false;

  @override
  void initState() {
    super.initState();
    _checkBiometricAvailable();
  }

  Future<void> _checkBiometricAvailable() async {
    final biometric = ref.read(biometricServiceProvider);
    final enabled = await biometric.isBiometricEnabled();
    final token = await biometric.getSavedToken();
    final canAuth = await biometric.canCheckBiometrics();
    if (mounted && enabled && (token != null && token.isNotEmpty) && canAuth) {
      setState(() => _showBiometricButton = true);
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _onLogin() async {
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    if (email.isEmpty) {
      setState(() => _error = '이메일을 입력하세요.');
      return;
    }
    if (password.isEmpty) {
      setState(() => _error = '비밀번호를 입력하세요.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final errorMsg = await ref.read(authStateProvider.notifier).login(email, password);
    if (mounted) {
      setState(() {
        _loading = false;
        _error = errorMsg;
      });
      if (errorMsg == null) {
        context.go('/');
      }
    }
  }

  Future<void> _onGoogleLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final googleSignIn = GoogleSignIn();
      final account = await googleSignIn.signIn();
      if (account == null) {
        if (mounted) setState(() => _loading = false);
        return;
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null) {
        if (mounted) setState(() {
          _loading = false;
          _error = '구글 인증 정보를 가져오지 못했습니다.';
        });
        return;
      }
      final errorMsg = await ref.read(authStateProvider.notifier).loginGoogle(idToken);
      if (mounted) {
        setState(() {
          _loading = false;
          _error = errorMsg;
        });
        if (errorMsg == null) {
          context.go('/');
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().contains('sign_in_canceled') ? null : '구글 로그인에 실패했습니다.';
        });
      }
    }
  }

  Future<void> _onKakaoLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      OAuthToken token = await UserApi.instance.loginWithKakaoAccount();
      final errorMsg = await ref.read(authStateProvider.notifier).loginKakao(token.accessToken);
      if (mounted) {
        setState(() {
          _loading = false;
          _error = errorMsg;
        });
        if (errorMsg == null) {
          context.go('/');
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.toString().contains('UserCancel') ? null : '카카오 로그인에 실패했습니다.';
        });
      }
    }
  }

  Future<void> _onBiometricLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    final errorMsg = await ref.read(authStateProvider.notifier).loginWithBiometric();
    if (mounted) {
      setState(() {
        _loading = false;
        _error = errorMsg;
      });
      if (errorMsg == null) {
        context.go('/');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal),
          child: Column(
            children: [
              const SizedBox(height: 48),
              Text(
                '배짱이',
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                '로그인하여 봇을 제어하세요',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.6),
                ),
              ),
              const Spacer(),
              if (_showBiometricButton) ...[
                FilledButton.tonalIcon(
                  onPressed: _loading ? null : _onBiometricLogin,
                  icon: const Icon(Icons.fingerprint, size: 24),
                  label: const Text('지문/얼굴로 로그인'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  '또는',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.6),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: theme.cardTheme.color ?? theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(AppTheme.radiusFocus),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.06),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _emailController,
                      decoration: const InputDecoration(
                        labelText: '이메일',
                        hintText: 'example@email.com',
                        prefixIcon: Icon(Icons.email_outlined),
                      ),
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _passwordController,
                      decoration: const InputDecoration(
                        labelText: '비밀번호',
                        prefixIcon: Icon(Icons.lock_outline),
                      ),
                      obscureText: true,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _onLogin(),
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        _error!,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.error,
                        ),
                        maxLines: 4,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _loading ? null : _onLogin,
                      child: _loading
                          ? const SizedBox(
                              height: 22,
                              width: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('로그인'),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _loading ? null : _onGoogleLogin,
                            icon: const Icon(Icons.g_mobiledata, size: 22),
                            label: const Text('구글'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _loading ? null : _onKakaoLogin,
                            icon: const Text('K', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                            label: const Text('카카오'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Center(
                      child: TextButton(
                        onPressed: () => context.push('/register'),
                        child: const Text('회원가입'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 48),
            ],
          ),
        ),
      ),
    );
  }
}
