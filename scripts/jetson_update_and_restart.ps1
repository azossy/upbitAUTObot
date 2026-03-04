# Jetson 백엔드 최신 코드 갱신 및 서비스 재시작
# 사용: PowerShell에서 이 스크립트 실행. SSH 비밀번호 입력 프롬프트가 뜨면 입력한 뒤, 원격에서 sudo 비밀번호를 묻으면 다시 입력.

$remote = "upbit@100.80.178.45"
$cmd = "cd ~/baejjangi && git pull && sudo systemctl restart baejjangi-backend && echo DONE && sudo systemctl status baejjangi-backend --no-pager"

Write-Host "Jetson($remote)에 접속해 git pull 및 baejjangi-backend 재시작을 실행합니다." -ForegroundColor Cyan
Write-Host "첫 번째: SSH 비밀번호, 두 번째: sudo 비밀번호(같을 수 있음)를 입력하세요." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no $remote $cmd
