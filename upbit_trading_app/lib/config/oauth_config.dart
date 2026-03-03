/// OAuth 클라이언트 설정. 실제 배포 시 .env 또는 빌드 시 주입으로 교체.
/// - 구글: Google Cloud Console에서 OAuth 클라이언트 ID 발급 (Android/iOS/Web)
/// - 카카오: Kakao Developers에서 앱 등록 후 네이티브 앱 키 발급
class OAuthConfig {
  /// 카카오 네이티브 앱 키 (Kakao Developers > 앱 > 앱 키)
  static const String kakaoNativeAppKey = 'YOUR_KAKAO_NATIVE_APP_KEY';
}
