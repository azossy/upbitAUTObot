@echo off
setlocal EnableDelayedExpansion
REM Baejjangi APK build - copy to English path then build (avoids Korean path + subst drive mix)

set FLUTTER=C:\flutter\bin\flutter.bat
if not exist "%FLUTTER%" (
  echo Flutter not found: C:\flutter\bin\flutter.bat
  exit /b 1
)

if not defined ANDROID_HOME set ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk
if not exist "%ANDROID_HOME%" (
  echo ANDROID_HOME not set. Install Android Studio and set SDK path.
  exit /b 1
)

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
set "APP_DIR=%PROJECT_ROOT%\upbit_trading_app"
set "BUILD_DIR=C:\dev\upbit_build"

echo Copying project to %BUILD_DIR% ...
if not exist "C:\dev" mkdir "C:\dev"
if exist "%BUILD_DIR%" rd /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"
xcopy /E /I /Q /Y "%APP_DIR%\*" "%BUILD_DIR%\" >nul
if %ERRORLEVEL% neq 0 (
  echo Copy failed.
  exit /b 1
)

echo Building APK at English path...
cd /d "%BUILD_DIR%"
"%FLUTTER%" pub get
"%FLUTTER%" build apk --release
set BUILD_EXIT=%ERRORLEVEL%

if %BUILD_EXIT% equ 0 (
  if not exist "%APP_DIR%\build\app\outputs\flutter-apk" mkdir "%APP_DIR%\build\app\outputs\flutter-apk"
  copy /Y "%BUILD_DIR%\build\app\outputs\flutter-apk\app-release.apk" "%APP_DIR%\build\app\outputs\flutter-apk\app-release.apk" >nul
  echo.
  echo APK saved to: %APP_DIR%\build\app\outputs\flutter-apk\app-release.apk
  rd /s /q "%BUILD_DIR%" 2>nul
) else (
  echo Build failed. Check log above.
)

exit /b %BUILD_EXIT%
