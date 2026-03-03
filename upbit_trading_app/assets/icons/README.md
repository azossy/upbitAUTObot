# 배짱이 앱 아이콘

- **소스**: `app_icon_1024.png` (1024×1024)
- **디자인 기준**: [Windows 앱 아이콘 디자인 지침](https://learn.microsoft.com/ko-kr/windows/apps/design/style/iconography/app-icon-design)

## 적용된 가이드라인

- **은유**: 상승 추세(차트/화살) → 트레이딩·성장을 한 가지 요소로 표현
- **형태**: 단순한 실루엣, 둥근 모서리, 작은 크기에서도 읽기 쉬움
- **색상**: 앱 프라이머리 #0381FE, 미묘한 그라데이션(좌상단 밝음)
- **대비**: 밝은/어두운 배경 모두에서 구분 가능하도록 구성

## 아이콘 생성 (Android / iOS / Web)

프로젝트 루트에서 다음을 실행하세요.

```bash
flutter pub get
dart run flutter_launcher_icons
```

생성 위치: `android/` mipmap, `ios/Runner/Assets.xcassets/AppIcon.appiconset`, `web/icons/`
