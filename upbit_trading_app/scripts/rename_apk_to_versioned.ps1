# pubspec.yaml 버전을 읽어 app-release.apk 를 baejjangi-X-Y-Z.apk 로 복사
# 사용: upbit_trading_app 폴더에서 .\scripts\rename_apk_to_versioned.ps1

$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$appDir\pubspec.yaml")) { Write-Error "pubspec.yaml not found in $appDir" }
$pubspec = Get-Content "$appDir\pubspec.yaml" -Raw
if ($pubspec -match "version:\s*([\d.]+)") { $ver = $Matches[1] } else { $ver = "1.0.0" }
$slug = $ver -replace "\.", "-"
$src = "$appDir\build\app\outputs\flutter-apk\app-release.apk"
$dst = "$appDir\build\app\outputs\flutter-apk\baejjangi-$slug.apk"
if (-not (Test-Path $src)) { Write-Error "APK not found: $src (run 'flutter build apk --release' first)" }
Copy-Item -Path $src -Destination $dst -Force
Write-Host "Created: $dst"
