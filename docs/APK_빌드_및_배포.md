# 배짱이 — APK 빌드 및 정식 배포

**저작자**: 차리 (challychoi@me.com)

Android 정식 배포용 APK를 빌드하고 GitHub Release에 올리는 방법입니다.

---

## 1. GitHub에서 자동 빌드 (권장)

저장소에는 **GitHub Actions** 워크플로가 포함되어 있습니다.  
**Release를 한 번 발행**하면, 자동으로 APK가 빌드되어 해당 Release에 첨부됩니다.

### 절차

1. GitHub **upbitAUTObot** 저장소 → **Releases** → **Create a new release**
2. **Tag**: `v1.0.0` (또는 새 버전, 예: `v1.0.1`)
3. **Release title**: 예) `배짱이 v1.0.0`
4. **Describe**: 원하는 설명 입력 (선택)
5. **Publish release** 클릭
6. 2~5분 정도 지나면 **Actions** 탭에서 빌드가 완료되고, 해당 Release 페이지에 **app-release.apk** 가 업로드됩니다.

이후 사용자는 **Releases** 페이지에서 APK를 내려받아 설치하면 됩니다.

---

## 2. 로컬에서 APK 빌드 (수동)

Flutter가 설치된 PC에서 직접 빌드할 때 사용합니다.

### 요구사항

- Flutter SDK 설치 및 `flutter` 명령어 사용 가능
- Android SDK (Android Studio 또는 standalone)

### 명령어

```bash
cd upbit_trading_app
flutter pub get
flutter build apk --release
```

생성된 파일: `build/app/outputs/flutter-apk/app-release.apk`

### 빌드 후 GitHub Release에 올리기

1. GitHub에서 해당 버전용 Release를 만든 뒤,
2. 로컬에서 GitHub CLI로 APK 첨부:

```bash
gh release upload v1.0.0 upbit_trading_app/build/app/outputs/flutter-apk/app-release.apk --repo azossy/upbitAUTObot
```

(버전 태그와 저장소는 실제 사용하는 값으로 바꾸세요.)

---

## 3. 정식 배포 시 체크

- **앱 서명**: Release 빌드는 `android/app/build.gradle` 의 `signingConfig` 에 따라 서명됩니다. 정식 배포용 키스토어가 설정되어 있어야 합니다.
- **버전**: `upbit_trading_app/pubspec.yaml` 의 `version` 과 `lib/constants/app_version.dart` 의 `kAppVersion` 을 배포 버전에 맞게 올려주세요.

현재 v1.0.0 기준으로 설정되어 있습니다.
