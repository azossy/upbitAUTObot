# 배짱이 — APK 빌드 및 정식 배포

**저작자**: 차리 (challychoi@me.com)

Android 정식 배포용 APK를 빌드하고 GitHub Release에 올리는 방법입니다.

**APK 파일명 규칙**: 빌드 결과물은 **`baejjangi-X-Y-Z.apk`** 형식으로 둡니다 (예: baejjangi-1-4-3.apk). `build_apk.bat` / `build_apk_로컬.bat` 실행 시 자동으로 버전별 파일명이 생성되며, 수동 빌드 후에는 `upbit_trading_app/scripts/rename_apk_to_versioned.ps1` 를 실행하면 됩니다.

**※ 정식 상용 배포용 앱**이므로, 테스트는 **크롬/웹이 아닌 APK 빌드 후 실기기 또는 에뮬레이터**로 진행해야 합니다.

---

## 1. 로컬에서 APK 직접 빌드 후 GitHub에 올리기 (빠름, 권장)

GitHub Actions는 빌드에 3~5분 걸리므로, **직접 컴파일해서 올리면** 바로 Release에 APK가 붙습니다.

### 요구사항

- **Flutter** SDK 설치 (예: `C:\flutter`)
- **Android SDK** (Android Studio 설치 시 함께 설치됨, `ANDROID_HOME` 또는 `C:\Users\본인계정\AppData\Local\Android\Sdk`)

### 방법 A: 배치 파일 + 수동 업로드 (Windows)

- **한글 경로**에 프로젝트가 있으면 AOT 빌드가 실패할 수 있습니다. 한글 경로 해결을 위해 프로젝트를 `c:\Users\chall\Desktop\myProject\upbitAUTObot`(폴더명: myProject, upbitAUTObot)으로 두는 것을 권장합니다. 123(화이트보드)의 「프로젝트 경로」 참고.  
  → **build_apk_로컬.bat** 을 사용하세요. (subst로 영문 경로에서 빌드해 한글 경로 이슈를 피합니다.)
1. `upbit_trading_app` 폴더에서 **build_apk_로컬.bat** 더블클릭 실행.  
   (Flutter 경로가 `C:\flutter\bin\flutter.bat` 이 아니면 파일 안의 `set FLUTTER=...` 를 수정하세요.)
2. 빌드가 끝나면 `upbit_trading_app\build\app\outputs\flutter-apk\baejjangi-1-4-3.apk`(예: 버전 1.4.3) 형식으로 생성됩니다. (버전마다 파일명이 `baejjangi-X-Y-Z.apk` 로 붙습니다.)
3. **GitHub CLI(gh)** 가 설치되어 있다면, 프로젝트 루트에서:
   ```powershell
   gh release upload v1.4.3 upbit_trading_app/build/app/outputs/flutter-apk/baejjangi-1-4-3.apk --repo azossy/upbitAUTObot --clobber
   ```
   (이미 v1.4.3 Release가 있어야 합니다. 없으면 먼저 `gh release create v1.4.3 --title "배짱이 v1.4.3"` 로 생성.)

### 방법 B: 한 번에 빌드 + 업로드 (PowerShell)

1. **GitHub CLI** 설치 및 `gh auth login` 완료.
2. `upbit_trading_app` 폴더에서 PowerShell을 열고:
   ```powershell
   .\upload_apk_to_github.ps1 v1.4.3
   ```
   이 스크립트는 Flutter로 APK를 빌드한 뒤, 지정한 태그의 Release에 `baejjangi-X-Y-Z.apk` 를 업로드합니다. (Flutter가 `C:\flutter\bin\flutter.bat` 에 있다고 가정)

### 수동 명령만 쓰고 싶을 때

```bash
cd upbit_trading_app
flutter pub get
flutter build apk --release
# 생성: build/app/outputs/flutter-apk/baejjangi-X-Y-Z.apk (예: baejjangi-1-4-3.apk)

# 업로드 (프로젝트 루트 또는 upbit_trading_app에서, 파일명은 실제 버전에 맞게)
gh release upload v1.4.3 build/app/outputs/flutter-apk/baejjangi-1-4-3.apk --repo azossy/upbitAUTObot --clobber
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
3. 약 5~7분 후 **Releases** 페이지에서 해당 버전의 **baejjangi-X-Y-Z.apk** 를 다운로드할 수 있습니다.

---

## 3. GitHub Actions로 자동 빌드 (Release를 수동으로 만든 경우)

Release를 웹에서 **Publish**해도 동일하게 APK가 빌드·첨부됩니다. (완료까지 약 5~7분)

1. **Releases** → **Create a new release** → Tag `v1.0.x` (또는 새 버전), 제목 입력 후 **Publish release**
2. **Actions** 탭에서 **Build Release APK** 완료 대기
3. Release 페이지에 **baejjangi-X-Y-Z.apk** 가 나타나면 다운로드 가능

---

## 4. 정식 배포 시 체크

- **앱 서명**: Release 빌드는 `android/app/build.gradle` 의 `signingConfig` 에 따라 서명됩니다. 정식 배포용 키스토어가 설정되어 있어야 합니다.
- **버전**: `upbit_trading_app/pubspec.yaml` 의 `version` 과 `lib/constants/app_version.dart` 의 `kAppVersion` 을 배포 버전에 맞게 올려주세요.

현재 v1.1.0 기준으로 설정되어 있습니다.

---

## 5. 정식 테스트 절차 (APK 기준)

상용 배포 전에는 반드시 **APK를 설치한 실기기 또는 에뮬레이터**에서 아래를 확인하세요.

1. **APK 빌드**  
   - `upbit_trading_app` 폴더에서 **build_apk_로컬.bat** 실행  
   - 또는 `flutter build apk --release` (한글/특수 경로 이슈 시 배치 파일 사용)

2. **설치**  
   - 생성된 `build/app/outputs/flutter-apk/app-release.apk` 를 USB로 전달하거나  
   - `adb install -r build/app/outputs/flutter-apk/app-release.apk` 로 에뮬/연결된 기기에 설치

3. **확인 항목**  
   - 앱 실행 시 스플래시("배짱이" + 로딩) 후 로그인 화면 전환  
   - 로그인·회원가입·대시보드·설정·API 서버 주소 변경 등 핵심 플로우  
   - 설정 → API 서버 주소에 백엔드 URL 입력 후 연동 테스트
