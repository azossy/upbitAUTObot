@echo off
REM 배짱이 v1.0 — Android APK 빌드
REM Android SDK가 설치되어 있어야 합니다. Android Studio 설치 시 함께 설치됩니다.

set FLUTTER=C:\flutter\bin\flutter.bat
if not exist "%FLUTTER%" (
  echo Flutter를 찾을 수 없습니다. C:\flutter\bin\flutter.bat 경로를 확인하세요.
  exit /b 1
)

REM Android SDK 경로 (Android Studio 기본 설치 위치)
if defined ANDROID_HOME goto :build
set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
if exist "%ANDROID_HOME%" goto :build
echo ANDROID_HOME이 설정되지 않았습니다.
echo Android Studio를 설치한 경우: 설정 - Android SDK 에서 SDK 경로를 확인한 뒤
echo    set ANDROID_HOME=경로
echo 를 입력하거나 이 파일에서 ANDROID_HOME을 수정하세요.
exit /b 1

:build
cd /d "%~dp0"
"%FLUTTER%" build apk --release
if %ERRORLEVEL% neq 0 exit /b 1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rename_apk_to_versioned.ps1"
echo.
echo APK 생성 완료: build\app\outputs\flutter-apk\baejjangi-X-Y-Z.apk (버전별 파일명)
