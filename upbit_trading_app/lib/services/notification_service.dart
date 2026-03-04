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
  FirebaseMessaging? _messaging;

  NotificationService(this._api);

  /// Firebase 미설정 시 null. 생성 시점에 instance 접근하지 않아 웹/미설정에서 크래시 방지.
  FirebaseMessaging? get _safeMessaging {
    if (_messaging != null) return _messaging;
    try {
      if (Firebase.apps.isEmpty) return null;
      _messaging = FirebaseMessaging.instance;
      return _messaging;
    } catch (_) {
      return null;
    }
  }

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
      final m = _safeMessaging;
      if (m == null) return null;
      return await m.getToken();
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
    final m = _safeMessaging;
    if (m != null) m.onTokenRefresh.listen(onToken);
  }

  /// 포그라운드 메시지 스트림 (Firebase 미설정 시 빈 스트림)
  Stream<RemoteMessage> get onMessage {
    final m = _safeMessaging;
    return m != null ? FirebaseMessaging.onMessage : const Stream.empty();
  }

  /// 알림 탭 시 (앱이 백그라운드/종료 상태에서 열림)
  Stream<RemoteMessage> get onMessageOpenedApp {
    final m = _safeMessaging;
    return m != null ? FirebaseMessaging.onMessageOpenedApp : const Stream.empty();
  }

  /// 앱이 종료된 상태에서 알림 탭으로 실행된 경우
  Future<RemoteMessage?> get initialMessage async {
    final m = _safeMessaging;
    return m != null ? await m.getInitialMessage() : null;
  }

  /// 알림 권한 요청 (iOS)
  Future<bool> requestPermission() async {
    final m = _safeMessaging;
    if (m == null) return false;
    final settings = await m.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );
    return settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
  }
}
