// FlutterFire CLI로 생성: flutterfire configure
// FCM 사용 시: dart pub global activate flutterfire_cli → flutterfire configure
// 실행 후 이 파일이 자동 생성됩니다. 현재는 FCM 없이 앱이 동작하도록 플레이스홀더입니다.

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    throw UnsupportedError(
      'Firebase 미설정. FCM 사용 시: flutterfire configure 실행',
    );
  }
}
