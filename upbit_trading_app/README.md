# 배짱이 v1.1

**저작자**: 차리 (challychoi@me.com)

Flutter 기반 Android 앱 (업비트 연동 자동매매).

## 사전 요구사항

- Flutter SDK 설치: https://docs.flutter.dev/get-started/install
- Android Studio 또는 VS Code + Flutter 확장

## 실행 방법

```bash
cd upbit_trading_app
flutter pub get
flutter run
```

## 프로젝트 구조

```
lib/
├── main.dart
├── app.dart
└── presentation/
    └── screens/     # 로그인, 대시보드, 포지션, 거래내역, 설정
```

## 현재 상태

- Mock 데이터로 UI 구현 완료
- 로그인 → 대시보드 → 하단 네비(포지션/거래/설정)
- 실제 API 연동은 Phase 4 이후 진행
