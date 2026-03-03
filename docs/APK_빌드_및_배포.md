# 배짱이 — APK 빌드 및 정식 배포

**저작자**: 차리 (challychoi@me.com)

Android 정식 배포용 APK를 빌드하고 GitHub Release에 올리는 방법입니다.

---

## 1. 로컬에서 APK 직접 빌드 후 GitHub에 올리기 (빠름, 권장)

GitHub Actions는 빌드에 3~5분 걸리므로, **직접 컴파일해서 올리면** 바로 Release에 APK가 붙습니다.

### 요구사항

- **Flutter** SDK 설치 (예: `C:\flutter`)
- **Android SDK** (Android Studio 설치 시 함께 설치됨, `ANDROID_HOME` 또는 `C:\Users\본인계정\AppData\Local\Android\Sdk`)

### 방법 A: 배치 파일 + 수동 업로드 (Windows)

- **한글 경로**(예: `파이썬공부방\업비트 자동매매`)에 프로젝트가 있으면 일반 **build_apk.bat** 은 AOT 빌드에서 실패할 수 있습니다.  
  → **build_apk_로컬.bat** 을 사용하세요. (subst로 영문 경로에서 빌드해 한글 경로 이슈를 피합니다.)
1. `upbit_trading_app` 폴더에서 **build_apk_로컬.bat** 더블클릭 실행.  
   (Flutter 경로가 `C:\flutter\bin\flutter.bat` 이 아니면 파일 안의 `set FLUTTER=...` 를 수정하세요.)
2. 빌드가 끝나면 `upbit_trading_app\build\app\outputs\flutter-apk\app-release.apk` 가 생성됩니다.
3. **GitHub CLI(gh)** 가 설치되어 있다면, 프로젝트 루트에서:
   ```powershell
   gh release upload v1.0.0 upbit_trading_app/build/app/outputs/flutter-apk/app-release.apk --repo azossy/upbitAUTObot --clobber
   ```
   (이미 v1.0.0 Release가 있어야 합니다. 없으면 먼저 `gh release create v1.0.0 --title "배짱이 v1.0.0"` 로 생성.)

### 방법 B: 한 번에 빌드 + 업로드 (PowerShell)

1. **GitHub CLI** 설치 및 `gh auth login` 완료.
2. `upbit_trading_app` 폴더에서 PowerShell을 열고:
   ```powershell
   .\upload_apk_to_github.ps1 v1.0.0
   ```
   이 스크립트는 Flutter로 APK를 빌드한 뒤, 지정한 태그의 Release에 `app-release.apk` 를 업로드합니다. (Flutter가 `C:\flutter\bin\flutter.bat` 에 있다고 가정)

### 수동 명령만 쓰고 싶을 때

```bash
cd upbit_trading_app
flutter pub get
flutter build apk --release
# 생성: build/app/outputs/flutter-apk/app-release.apk

# 업로드 (프로젝트 루트 또는 upbit_trading_app에서)
gh release upload v1.0.0 build/app/outputs/flutter-apk/app-release.apk --repo azossy/upbitAUTObot --clobber
```

---

## 2. 방법 B — 태그 푸시로 자동 Release + APK 빌드 (권장)

**버전 태그만 푸시하면** Release가 자동 생성되고, APK가 빌드되어 해당 Release에 붙습니다.

```bash
# 프로젝트 루트에서 (예: v1.0.4)
git tag v1.0.4
git push origin v1.0.4
```

1. **Auto Release on Tag** 워크플로가 해당 태그로 Release를 생성·발행합니다.
2. **Build Release APK** 워크플로가 자동으로 실행되어 APK를 빌드하고, 그 Release에 업로드합니다.
3. 약 5~7분 후 **Releases** 페이지에서 해당 버전의 **app-release.apk** 를 다운로드할 수 있습니다.

---

## 3. GitHub Actions로 자동 빌드 (Release를 수동으로 만든 경우)

Release를 웹에서 **Publish**해도 동일하게 APK가 빌드·첨부됩니다. (완료까지 약 5~7분)

1. **Releases** → **Create a new release** → Tag `v1.0.x` (또는 새 버전), 제목 입력 후 **Publish release**
2. **Actions** 탭에서 **Build Release APK** 완료 대기
3. Release 페이지에 **app-release.apk** 가 나타나면 다운로드 가능

---

## 4. 정식 배포 시 체크

- **앱 서명**: Release 빌드는 `android/app/build.gradle` 의 `signingConfig` 에 따라 서명됩니다. 정식 배포용 키스토어가 설정되어 있어야 합니다.
- **버전**: `upbit_trading_app/pubspec.yaml` 의 `version` 과 `lib/constants/app_version.dart` 의 `kAppVersion` 을 배포 버전에 맞게 올려주세요.

현재 v1.0.0 기준으로 설정되어 있습니다.
