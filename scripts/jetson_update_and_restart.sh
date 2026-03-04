#!/bin/bash
# Jetson 백엔드 최신 코드 갱신 및 서비스 재시작
# 사용: ssh upbit@100.80.178.45 'bash -s' < scripts/jetson_update_and_restart.sh
# 또는 Jetson에 로그인한 뒤: cd ~/baejjangi && git pull && sudo systemctl restart baejjangi-backend

set -e
cd ~/baejjangi || { echo "디렉터리 없음: ~/baejjangi"; exit 1; }
git pull
sudo systemctl restart baejjangi-backend
echo "완료. 상태 확인: sudo systemctl status baejjangi-backend"
