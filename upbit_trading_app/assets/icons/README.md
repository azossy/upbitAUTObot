# 배짱이 앱 아이콘

- **소스**: `app_icon_1024.png` (1024×1024) — **오렌지 배경(#FF6B00) + 흰색 한글 "배짱이"** 단순 텍스트 아이콘 (캐릭터 없음)
- **런처 배경**: `android/.../values/colors.xml` → `ic_launcher_background` #FF6B00
- **디자인 기준**: docs/UI_UX_가이드_적용.md

## 아이콘 생성 (Android / iOS / Web)

프로젝트 루트에서 다음을 실행하세요.

```bash
flutter pub get
dart run flutter_launcher_icons
```

생성 위치: `android/` mipmap, `ios/Runner/Assets.xcassets/AppIcon.appiconset`, `web/icons/`
