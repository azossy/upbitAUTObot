import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'app.dart';
import 'config/oauth_config.dart';
import 'services/notification_service.dart';
import 'theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // 빌드 예외 시 회색 화면 대신 오류 메시지 표시
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return Material(
      color: AppTheme.surfaceLight,
      child: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('배짱이', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primary)),
                  const SizedBox(height: 16),
                  Text(details.exceptionAsString(), style: const TextStyle(fontSize: 12, color: Colors.red)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  };
  KakaoSdk.init(nativeAppKey: OAuthConfig.kakaoNativeAppKey);
  // Firebase는 비동기로 초기화 (블로킹 시 빈 화면 방지)
  NotificationService.initialize().then((_) {}).catchError((_) {});
  runApp(const ProviderScope(child: UpbitTradingApp()));
}
