import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'api_service.dart';
import 'biometric_service.dart';
import 'notification_service.dart';

/// 구글/카카오 로그인 결과. 성공(로그인됨) / 미가입(회원가입 화면으로) / 실패(에러 메시지)
class OAuthLoginResult {
  final bool success;
  final bool needRegister;
  final String? errorMessage;
  final String? email;
  final String? name;
  final String? idToken;
  final String? accessToken;
  final String? provider; // 'google' | 'kakao'

  OAuthLoginResult._({this.success = false, this.needRegister = false, this.errorMessage, this.email, this.name, this.idToken, this.accessToken, this.provider});

  factory OAuthLoginResult.success() => OAuthLoginResult._(success: true);
  factory OAuthLoginResult.needRegister({required String email, required String name, String? idToken, String? accessToken, required String provider}) =>
      OAuthLoginResult._(needRegister: true, email: email, name: name, idToken: idToken, accessToken: accessToken, provider: provider);
  factory OAuthLoginResult.failure(String message) => OAuthLoginResult._(errorMessage: message);
}

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());
final biometricServiceProvider = Provider<BiometricService>((ref) => BiometricService());
final notificationServiceProvider = Provider<NotificationService>((ref) => NotificationService(ref.watch(apiServiceProvider)));

final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(
    ref.watch(apiServiceProvider),
    ref.watch(biometricServiceProvider),
    ref.watch(notificationServiceProvider),
  );
});

class AuthState {
  final bool isLoggedIn;
  final Map<String, dynamic>? user;

  AuthState({this.isLoggedIn = false, this.user});

  AuthState copyWith({bool? isLoggedIn, Map<String, dynamic>? user}) {
    return AuthState(
      isLoggedIn: isLoggedIn ?? this.isLoggedIn,
      user: user ?? this.user,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiService _api;
  final BiometricService _biometric;
  final NotificationService _notification;

  AuthNotifier(this._api, this._biometric, this._notification) : super(AuthState());

  void _onLoginSuccess(String token, Map<String, dynamic> user) async {
    _api.setToken(token);
    state = AuthState(isLoggedIn: true, user: user);
    if (await _biometric.isBiometricEnabled()) {
      await _biometric.saveToken(token);
    }
    await _notification.registerOnLogin();
  }

  /// 로그인 시도. 성공 시 null, 실패 시 에러 메시지 반환.
  Future<String?> login(String email, String password) async {
    try {
      final data = await _api.login(email, password);
      final token = data['access_token'] as String?;
      final user = data['user'] as Map<String, dynamic>?;
      if (token != null && user != null) {
        _onLoginSuccess(token, user);
        return null;
      }
      return '서버 응답 형식 오류';
    } on DioException catch (e) {
      if (e.response?.statusCode == 403) {
        final data = e.response?.data;
        if (data is Map && data['remaining_minutes'] != null) {
          final n = data['remaining_minutes'] is int
              ? data['remaining_minutes'] as int
              : int.tryParse(data['remaining_minutes'].toString()) ?? 15;
          return '계정이 일시 잠금되었습니다. $n분 후 다시 시도해 주세요.';
        }
        return '계정이 일시 잠금되었습니다. 15분 후 다시 시도해 주세요.';
      }
      if (e.response?.statusCode == 401) {
        return '이메일 또는 비밀번호를 확인하세요.';
      }
      return getApiErrorMessage(e, fallback: '로그인에 실패했습니다.');
    } catch (e) {
      return getApiErrorMessage(e, fallback: '로그인에 실패했습니다.');
    }
  }

  /// 구글 로그인. 성공(로그인됨) / needRegister(회원가입 화면으로) / failure(에러 메시지).
  Future<OAuthLoginResult> loginGoogle(String idToken) async {
    try {
      final data = await _api.loginGoogle(idToken);
      if (data['need_register'] == true) {
        return OAuthLoginResult.needRegister(
          email: data['email']?.toString() ?? '',
          name: data['name']?.toString() ?? '',
          idToken: idToken,
          provider: 'google',
        );
      }
      final token = data['access_token'] as String?;
      final user = data['user'] as Map<String, dynamic>?;
      if (token != null && user != null) {
        _onLoginSuccess(token, user);
        return OAuthLoginResult.success();
      }
      return OAuthLoginResult.failure('서버 응답 형식 오류');
    } on DioException catch (e) {
      return OAuthLoginResult.failure(getApiErrorMessage(e, fallback: '구글 로그인에 실패했습니다.'));
    } catch (e) {
      return OAuthLoginResult.failure(getApiErrorMessage(e, fallback: '구글 로그인에 실패했습니다.'));
    }
  }

  /// 카카오 로그인. 성공(로그인됨) / needRegister(회원가입 화면으로) / failure(에러 메시지).
  Future<OAuthLoginResult> loginKakao(String accessToken) async {
    try {
      final data = await _api.loginKakao(accessToken);
      if (data['need_register'] == true) {
        return OAuthLoginResult.needRegister(
          email: data['email']?.toString() ?? '',
          name: data['name']?.toString() ?? '',
          accessToken: accessToken,
          provider: 'kakao',
        );
      }
      final token = data['access_token'] as String?;
      final user = data['user'] as Map<String, dynamic>?;
      if (token != null && user != null) {
        _onLoginSuccess(token, user);
        return OAuthLoginResult.success();
      }
      return OAuthLoginResult.failure('서버 응답 형식 오류');
    } on DioException catch (e) {
      return OAuthLoginResult.failure(getApiErrorMessage(e, fallback: '카카오 로그인에 실패했습니다.'));
    } catch (e) {
      return OAuthLoginResult.failure(getApiErrorMessage(e, fallback: '카카오 로그인에 실패했습니다.'));
    }
  }

  /// OAuth 회원가입 완료 (닉네임 입력 후). 성공 시 로그인 처리 후 null, 실패 시 에러 메시지.
  Future<String?> completeOAuthRegister({
    required String provider,
    String? idToken,
    String? accessToken,
    required String nickname,
  }) async {
    try {
      Map<String, dynamic> data;
      if (provider == 'google' && idToken != null) {
        data = await _api.completeGoogleRegister(idToken, nickname);
      } else if (provider == 'kakao' && accessToken != null) {
        data = await _api.completeKakaoRegister(accessToken, nickname);
      } else {
        return '잘못된 요청입니다.';
      }
      final token = data['access_token'] as String?;
      final user = data['user'] as Map<String, dynamic>?;
      if (token != null && user != null) {
        _onLoginSuccess(token, user);
        return null;
      }
      return '서버 응답 형식 오류';
    } on DioException catch (e) {
      return getApiErrorMessage(e, fallback: '가입 처리 중 오류가 발생했습니다. 닉네임을 확인한 뒤 다시 시도해 주세요.');
    } catch (e) {
      return getApiErrorMessage(e, fallback: '가입 처리 중 오류가 발생했습니다. 닉네임을 확인한 뒤 다시 시도해 주세요.');
    }
  }

  /// 생체인증으로 저장된 토큰 복원. 성공 시 null, 실패 시 에러 메시지.
  Future<String?> loginWithBiometric() async {
    try {
      final token = await _biometric.getSavedToken();
      if (token == null || token.isEmpty) return '저장된 로그인 정보가 없습니다.';
      final ok = await _biometric.authenticate(reason: '로그인을 위해 인증해 주세요');
      if (!ok) return '인증이 취소되었습니다.';
      _api.setToken(token);
      final data = await _api.getMe();
      state = AuthState(isLoggedIn: true, user: {
        'id': data['id'],
        'email': data['email'],
        'nickname': data['nickname'],
        'role': data['role'],
      });
      await _notification.registerOnLogin();
      return null;
    } catch (e) {
      return getApiErrorMessage(e, fallback: '생체인증 로그인에 실패했습니다.');
    }
  }

  /// 회원가입. 성공 시 null, 실패 시 에러 메시지 반환 (한글, detail 파싱)
  Future<String?> register(String email, String password, String nickname) async {
    try {
      await _api.register(email, password, nickname);
      return null;
    } on DioException catch (e) {
      return getApiErrorMessage(e, fallback: '가입 처리에 실패했습니다. 입력 내용을 확인한 뒤 다시 시도해 주세요.');
    } catch (e) {
      return getApiErrorMessage(e, fallback: '가입 처리에 실패했습니다. 입력 내용을 확인한 뒤 다시 시도해 주세요.');
    }
  }

  /// 회원가입 1단계: 인증 메일 발송. 성공 시 null, 실패 시 에러 메시지.
  Future<String?> sendVerificationEmail(String email) async {
    try {
      await _api.sendVerificationEmail(email);
      return null;
    } on DioException catch (e) {
      return getApiErrorMessage(e, fallback: '인증 메일을 보내지 못했습니다. 이메일 주소를 확인하거나 잠시 후 다시 시도해 주세요.');
    } catch (e) {
      return getApiErrorMessage(e, fallback: '인증 메일을 보내지 못했습니다. 이메일 주소를 확인하거나 잠시 후 다시 시도해 주세요.');
    }
  }

  /// 회원가입 2단계: 인증 번호 확인 후 가입 완료. 성공 시 null, 실패 시 에러 메시지.
  Future<String?> verifyAndRegister({
    required String email,
    required String password,
    required String nickname,
    required String code,
  }) async {
    try {
      await _api.verifyAndRegister(
        email: email,
        password: password,
        nickname: nickname,
        code: code,
      );
      return null;
    } on DioException catch (e) {
      return getApiErrorMessage(e, fallback: '가입에 실패했습니다.');
    } catch (e) {
      return getApiErrorMessage(e, fallback: '가입에 실패했습니다.');
    }
  }

  void logout() {
    _api.clearToken();
    _biometric.clearSavedToken();
    state = AuthState();
  }
}
