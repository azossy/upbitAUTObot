import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 생체인증 로그인 및 토큰 보안 저장
class BiometricService {
  static const _keyBiometricEnabled = 'biometric_login_enabled';
  static const _keySavedToken = 'saved_auth_token';

  final LocalAuthentication _localAuth = LocalAuthentication();
  final FlutterSecureStorage _secureStorage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  /// 생체인증 사용 가능 여부
  Future<bool> canCheckBiometrics() async {
    try {
      return await _localAuth.canCheckBiometrics;
    } catch (_) {
      return false;
    }
  }

  /// 등록된 생체인증(지문/얼굴) 존재 여부
  Future<bool> isDeviceSupported() async {
    try {
      return await _localAuth.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  /// 생체인증으로 인증 (지문/얼굴)
  Future<bool> authenticate({String reason = '로그인을 위해 인증해 주세요'}) async {
    try {
      return await _localAuth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }

  /// 설정: 생체정보 로그인 사용 여부
  Future<bool> isBiometricEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyBiometricEnabled) ?? false;
  }

  Future<void> setBiometricEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyBiometricEnabled, enabled);
    if (!enabled) {
      await _secureStorage.delete(key: _keySavedToken);
    }
  }

  /// 토큰 저장 (생체인증 활성화 시 로그인 성공 후 호출)
  Future<void> saveToken(String token) async {
    await _secureStorage.write(key: _keySavedToken, value: token);
  }

  /// 저장된 토큰 조회 (생체인증 성공 후)
  Future<String?> getSavedToken() async {
    return await _secureStorage.read(key: _keySavedToken);
  }

  /// 저장된 토큰 삭제 (로그아웃 시)
  Future<void> clearSavedToken() async {
    await _secureStorage.delete(key: _keySavedToken);
  }
}
