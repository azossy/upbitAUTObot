// FCM 푸시 알림 — 토큰 발급, 서버 등록, 포그라운드/백그라운드 처리
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../firebase_options.dart';
import 'api_service.dart';

/// 백그라운드 메시지 핸들러 (앱이 종료/백그라운드일 때 — 별도 isolate)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  try {
    if (Firebase.apps.isEmpty) {
      await Firebase.initializeApp(); // 플랫폼 기본 설정 사용 (google-services.json 등)
    }
  } catch (_) {}
}

class NotificationService {
  final ApiService _api;
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  NotificationService(this._api);

  /// Firebase 초기화 및 FCM 설정 (실패 시에도 앱은 정상 동작)
  static Future<bool> initialize() async {
    try {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      await FirebaseMessaging.instance.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
      return true;
    } catch (e) {
      debugPrint('[FCM] 초기화 실패 (flutterfire configure 필요): $e');
      return false;
    }
  }

  /// FCM 토큰 발급
  Future<String?> getToken() async {
    try {
      if (Firebase.apps.isEmpty) return null;
      return await _messaging.getToken();
    } catch (e) {
      debugPrint('[FCM] 토큰 발급 실패: $e');
      return null;
    }
  }

  /// 서버에 FCM 토큰 등록
  Future<bool> registerTokenToServer(String token) async {
    try {
      await _api.registerFcmToken(token);
      return true;
    } catch (e) {
      debugPrint('[FCM] 서버 등록 실패: $e');
      return false;
    }
  }

  /// 로그인 후 호출: 토큰 발급 후 서버 등록
  Future<void> registerOnLogin() async {
    final token = await getToken();
    if (token != null) await registerTokenToServer(token);
  }

  /// 토큰 갱신 리스너 (주기적 갱신 시 서버에 재등록)
  void onTokenRefresh(void Function(String) onToken) {
    _messaging.onTokenRefresh.listen(onToken);
  }

  /// 포그라운드 메시지 스트림
  Stream<RemoteMessage> get onMessage => FirebaseMessaging.onMessage;

  /// 알림 탭 시 (앱이 백그라운드/종료 상태에서 열림)
  Stream<RemoteMessage> get onMessageOpenedApp => FirebaseMessaging.onMessageOpenedApp;

  /// 앱이 종료된 상태에서 알림 탭으로 실행된 경우
  Future<RemoteMessage?> get initialMessage async =>
      await FirebaseMessaging.instance.getInitialMessage();

  /// 알림 권한 요청 (iOS)
  Future<bool> requestPermission() async {
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    return settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
  }
}
