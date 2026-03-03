# 배짱이 APK 빌드 후 GitHub Release에 업로드
# 사용법: PowerShell에서 .\upload_apk_to_github.ps1 [태그]   예: .\upload_apk_to_github.ps1 v1.0.0

param([string]$Tag = "v1.0.0")

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$flutter = "C:\flutter\bin\flutter.bat"
if (-not (Test-Path $flutter)) {
    Write-Host "Flutter를 찾을 수 없습니다: $flutter"
    Write-Host "먼저 upbit_trading_app\build_apk.bat 를 실행해 APK를 빌드한 뒤,"
    Write-Host "아래 명령으로 수동 업로드하세요:"
    Write-Host "  gh release upload $Tag build\app\outputs\flutter-apk\app-release.apk --repo azossy/upbitAUTObot --clobber"
    exit 1
}

Write-Host "APK 빌드 중..."
& $flutter pub get
& $flutter build apk --release
if ($LASTEXITCODE -ne 0) {
    Write-Host "빌드 실패. Android SDK(ANDROID_HOME) 설정을 확인하세요."
    exit 1
}

$apk = "build\app\outputs\flutter-apk\app-release.apk"
if (-not (Test-Path $apk)) {
    Write-Host "APK 파일을 찾을 수 없습니다: $apk"
    exit 1
}

Write-Host "GitHub Release에 업로드 중: $Tag"
gh release upload $Tag $apk --repo azossy/upbitAUTObot --clobber
if ($LASTEXITCODE -ne 0) {
    Write-Host "업로드 실패. gh 로그인 여부와 Release 존재 여부를 확인하세요."
    Write-Host "Release가 없으면: gh release create $Tag --title `"배짱이 $Tag`""
    exit 1
}

Write-Host "완료. https://github.com/azossy/upbitAUTObot/releases/tag/$Tag 에서 확인하세요."
