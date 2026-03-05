import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/auth_provider.dart';
import '../../theme/app_theme.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  /// OAuth(구글/카카오) 로그인 후 미가입 시 회원가입 완료 모드. 널이면 일반 이메일 회원가입.
  final OAuthLoginResult? oauthResult;

  const RegisterScreen({super.key, this.oauthResult});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _emailController = TextEditingController();
  final _nicknameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _codeController = TextEditingController();
  bool _loading = false;
  bool _resendLoading = false;
  String? _error;
  bool _obscurePassword = true;
  /// 1: 환영·이메일·닉네임·비밀번호(한 화면), 2: 인증 코드
  int _step = 1;
  bool _registrationSuccess = false;
  /// OAuth(구글/카카오) 미가입 사용자 추가 정보 입력 모드
  bool _isOAuthMode = false;

  @override
  void initState() {
    super.initState();
    if (widget.oauthResult != null) {
      _isOAuthMode = true;
      _emailController.text = widget.oauthResult!.email ?? '';
      _nicknameController.text = widget.oauthResult!.name ?? '';
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _nicknameController.dispose();
    _passwordController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  static final _emailRegex = RegExp(r'^[\w.-]+@[\w.-]+\.\w+$');

  /// Step 1: 이메일·닉네임·비밀번호 검증 후 인증 메일 발송 요청 (한 화면에서 완료)
  Future<void> _onRequestVerificationEmail() async {
    final email = _emailController.text.trim();
    final nickname = _nicknameController.text.trim();
    final password = _passwordController.text;
    if (email.isEmpty) {
      setState(() => _error = '이메일을 입력하세요.');
      return;
    }
    if (!_emailRegex.hasMatch(email)) {
      setState(() => _error = '올바른 이메일 형식을 입력하세요.');
      return;
    }
    if (nickname.isEmpty) {
      setState(() => _error = '닉네임을 입력하세요.');
      return;
    }
    if (nickname.length > 100) {
      setState(() => _error = '닉네임은 100자 이내로 입력하세요.');
      return;
    }
    if (password.length < 8) {
      setState(() => _error = '비밀번호는 8자 이상 입력하세요.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final errorMsg = await ref.read(authStateProvider.notifier).sendVerificationEmail(email);
    if (mounted) {
      setState(() {
        _loading = false;
        if (errorMsg != null) {
          _error = errorMsg;
        } else {
          _step = 2;
          _error = null;
          _codeController.clear();
        }
      });
      if (mounted && errorMsg != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg), duration: const Duration(seconds: 4)),
        );
      }
    }
  }

  /// Step 3: 인증코드 재발송 (1분 경과 또는 코드 인증 실패 시)
  Future<void> _onResendCode() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) return;
    setState(() {
      _resendLoading = true;
      _error = null;
    });
    final errorMsg = await ref.read(authStateProvider.notifier).sendVerificationEmail(email);
    if (mounted) {
      setState(() => _resendLoading = false);
      if (errorMsg != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg), duration: const Duration(seconds: 4)),
        );
      } else {
        _codeController.clear();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('인증 코드를 다시 발송했습니다. 메일함을 확인해 주세요.'),
            duration: Duration(seconds: 3),
          ),
        );
      }
    }
  }

  Future<void> _onVerifyAndRegister() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      setState(() => _error = '인증 번호를 입력하세요.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final email = _emailController.text.trim();
    final nickname = _nicknameController.text.trim();
    final password = _passwordController.text;
    final errorMsg = await ref.read(authStateProvider.notifier).verifyAndRegister(
          email: email,
          password: password,
          nickname: nickname,
          code: code,
        );
    if (mounted) {
      setState(() {
        _loading = false;
        if (errorMsg == null) {
          _registrationSuccess = true;
          _error = null;
        } else {
          _error = errorMsg;
        }
      });
      if (mounted && errorMsg != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg), duration: const Duration(seconds: 4)),
        );
      }
    }
  }

  void _handleBack(BuildContext context) {
    if (_isOAuthMode) {
      if (context.mounted) Navigator.of(context).pop();
      return;
    }
    if (_step == 2) {
      setState(() {
        _step = 1;
        _error = null;
      });
    } else {
      if (context.mounted) Navigator.of(context).pop();
    }
  }

  /// OAuth(구글/카카오) 회원가입 완료: 닉네임만 입력받고 가입
  Future<void> _onCompleteOAuthRegister() async {
    final nickname = _nicknameController.text.trim();
    if (nickname.isEmpty) {
      setState(() => _error = '닉네임을 입력하세요.');
      return;
    }
    if (nickname.length > 100) {
      setState(() => _error = '닉네임은 100자 이내로 입력하세요.');
      return;
    }
    final oauth = widget.oauthResult!;
    setState(() {
      _loading = true;
      _error = null;
    });
    final errorMsg = await ref.read(authStateProvider.notifier).completeOAuthRegister(
      provider: oauth.provider!,
      idToken: oauth.idToken,
      accessToken: oauth.accessToken,
      nickname: nickname,
    );
    if (!mounted) return;
    setState(() => _loading = false);
    if (errorMsg != null) {
      setState(() => _error = errorMsg);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorMsg), duration: const Duration(seconds: 4)));
      return;
    }
    if (mounted) Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, dynamic _) {
        if (!didPop) _handleBack(context);
      },
      child: Scaffold(
        appBar: AppBar(
          title: const Text('회원가입'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => _handleBack(context),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: AppTheme.marginHorizontal),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),
                if (_registrationSuccess) _buildSuccessContent(theme)
                else if (_isOAuthMode) _buildOAuthCompleteContent(theme)
                else _buildStepContent(theme),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSuccessContent(ThemeData theme) {
    return Container(
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
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '축하합니다! 인증되었습니다.',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '로그인 화면에서 정식 로그인을 하시면 됩니다.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.8),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () {
              if (context.mounted) Navigator.of(context).pop();
            },
            child: const Text('확인'),
          ),
        ],
      ),
    );
  }

  /// 구글/카카오 로그인 후 미가입 시: 이메일(읽기 전용) + 닉네임 입력 → 가입 완료
  Widget _buildOAuthCompleteContent(ThemeData theme) {
    final oauth = widget.oauthResult!;
    final providerName = oauth.provider == 'google' ? '구글' : '카카오';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$providerName 계정으로 가입하기',
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: theme.colorScheme.primary,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          '아래 닉네임을 입력한 뒤 가입을 완료하세요. 다음부터는 $providerName으로 자동 로그인됩니다.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.8),
          ),
        ),
        const SizedBox(height: 20),
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
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _emailController,
                readOnly: true,
                decoration: const InputDecoration(
                  labelText: '이메일',
                  prefixIcon: Icon(Icons.email_outlined),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _nicknameController,
                decoration: const InputDecoration(
                  labelText: '닉네임',
                  hintText: '한글·영문 사용 가능',
                  prefixIcon: Icon(Icons.person_outline),
                ),
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _onCompleteOAuthRegister(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.error),
                ),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _loading ? null : _onCompleteOAuthRegister,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('가입 완료'),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStepContent(ThemeData theme) {
    if (_step == 1) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '환영합니다!!',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '업비트 자동매매를 쉽고 안전하게 도와주는 배짱이와 함께하세요.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.8),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            '이메일, 닉네임, 비밀번호를 입력한 뒤 아래에서 인증 메일을 요청하세요.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.8),
            ),
          ),
          const SizedBox(height: 20),
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
                  controller: _nicknameController,
                  decoration: const InputDecoration(
                    labelText: '닉네임',
                    hintText: '한글·영문 사용 가능',
                    prefixIcon: Icon(Icons.person_outline),
                  ),
                  keyboardType: TextInputType.text,
                  textInputAction: TextInputAction.next,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordController,
                  decoration: InputDecoration(
                    labelText: '비밀번호 (8자 이상)',
                    hintText: '8자 이상 입력',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      ),
                      onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
                    ),
                  ),
                  obscureText: _obscurePassword,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => _onRequestVerificationEmail(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 20),
                Text(
                  '아래 버튼을 누르면 입력한 이메일로 인증 번호가 발송됩니다.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _loading ? null : _onRequestVerificationEmail,
                  child: _loading
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('인증 메일 받기'),
                ),
              ],
            ),
          ),
        ],
      );
    }

    // _step == 2: 인증 코드 입력
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_error != null) ...[
          Text(
            _error!,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.error,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 12),
        ],
        Text(
          '신청한 메일 주소로 인증 번호를 발송했습니다.',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '메일함을 열어 6자리 코드를 확인한 뒤 아래에 입력해 주세요.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.85),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          '도착하지 않았다면 스팸함을 확인해 주세요.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.6),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          '입력 시간(1분)이 지났거나 코드 인증에 문제가 있으면 아래에서 재발송을 요청하세요.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurface.withOpacity(0.7),
          ),
        ),
        const SizedBox(height: 20),
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
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '발송 대상: ${_emailController.text.trim()}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurface.withOpacity(0.7),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _codeController,
                decoration: const InputDecoration(
                  labelText: '인증 번호 (6자리)',
                  hintText: '6자리 코드',
                  prefixIcon: Icon(Icons.pin_outlined),
                ),
                keyboardType: TextInputType.number,
                maxLength: 6,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _onVerifyAndRegister(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Center(
                child: TextButton.icon(
                  onPressed: (_resendLoading || _loading) ? null : _onResendCode,
                  icon: _resendLoading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.refresh, size: 20),
                  label: Text(_resendLoading ? '재발송 중…' : '인증코드 재발송'),
                ),
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _loading ? null : _onVerifyAndRegister,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('확인'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
