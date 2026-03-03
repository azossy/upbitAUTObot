import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'app.dart';
import 'config/oauth_config.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  KakaoSdk.init(nativeAppKey: OAuthConfig.kakaoNativeAppKey);
  // Firebase는 비동기로 초기화 (블로킹 시 빈 화면 방지)
  NotificationService.initialize().then((_) {}).catchError((_) {});
  runApp(const ProviderScope(child: UpbitTradingApp()));
}
