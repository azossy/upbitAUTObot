/// OAuth 클라이언트 설정. 실제 배포 시 환경별로 설정.
/// - 구글: Google Cloud Console에서 OAuth 클라이언트 ID 발급 (Android + Web 동일 프로젝트)
///   · Web 클라이언트 ID를 앱의 serverClientId와 백엔드 GOOGLE_CLIENT_ID에 동일하게 사용 (공식 권장)
/// - 카카오: Kakao Developers에서 앱 등록 후 네이티브 앱 키 발급
class OAuthConfig {
  /// 구글 Web 클라이언트 ID (서버 검증용). 백엔드 .env의 GOOGLE_CLIENT_ID와 동일 값.
  /// 없으면 id_token이 null일 수 있음. Google Cloud Console > API 및 서비스 > 사용자 인증 정보 > 웹 클라이언트
  static const String googleWebClientId = 'YOUR_GOOGLE_WEB_CLIENT_ID.apps.googleusercontent.com';

  /// 카카오 네이티브 앱 키 (Kakao Developers > 앱 > 앱 키)
  static const String kakaoNativeAppKey = 'YOUR_KAKAO_NATIVE_APP_KEY';

  /// 구글 로그인 사용 가능 여부 (실제 Web Client ID가 설정된 경우만 true)
  static bool get isGoogleConfigured =>
      googleWebClientId.isNotEmpty &&
      !googleWebClientId.startsWith('YOUR_') &&
      googleWebClientId.contains('googleusercontent.com');

  /// 카카오 로그인 사용 가능 여부 (실제 네이티브 앱 키가 설정된 경우만 true)
  static bool get isKakaoConfigured =>
      kakaoNativeAppKey.isNotEmpty && !kakaoNativeAppKey.startsWith('YOUR_');
}
