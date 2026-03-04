import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'app.dart';
import 'config/oauth_config.dart';
import 'services/notification_service.dart';
import 'theme/app_theme.dart';

/// 루트에서 첫 프레임에 무조건 스플래시를 그려 빈 화면 방지. (Riverpod·GoRouter 의존 없음)
class _SplashGate extends StatefulWidget {
  const _SplashGate();

  @override
  State<_SplashGate> createState() => _SplashGateState();
}

class _SplashGateState extends State<_SplashGate> {
  bool _showApp = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) setState(() => _showApp = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_showApp) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        home: Scaffold(
          backgroundColor: const Color(0xFFFAFAFA),
          body: SafeArea(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    '배짱이',
                    style: TextStyle(
                      fontSize: 26,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF0381FE),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    '로딩 중…',
                    style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }
    return const ProviderScope(child: UpbitTradingApp());
  }
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return Material(
      color: const Color(0xFFFAFAFA),
      child: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    '배짱이',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF0381FE)),
                  ),
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
  try {
    KakaoSdk.init(nativeAppKey: OAuthConfig.kakaoNativeAppKey);
  } catch (_) {}
  NotificationService.initialize().then((_) {}).catchError((_) {});
  runApp(const _SplashGate());
}
