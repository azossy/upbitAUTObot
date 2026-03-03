# GitHub Actions — Release APK 업로드 403 해결

**저작자**: 차리 (challychoi@me.com)

APK 빌드는 성공하는데 `gh release upload` 단계에서 **HTTP 403**이 나면, 아래를 순서대로 확인하세요.

---

## 1. 저장소 설정 (가장 흔한 원인)

GitHub에서 **워크플로가 쓸 수 있는 권한**이 **읽기 전용**으로 제한돼 있으면, 워크플로에 `permissions: contents: write`를 넣어도 403이 날 수 있습니다.

### 확인·수정 방법

1. **upbitAUTObot** 저장소 페이지에서 **Settings** 이동  
2. 왼쪽 **Actions** → **General**  
3. **Workflow permissions** 섹션 찾기  
4. **"Read and write permissions"** 선택  
   - 기본값이 "Read repository contents and packages permissions only"이면 **쓰기 불가**라서 Release 업로드 시 403 발생  
5. **Save** 클릭  

이후 **새로 실행**되는 워크플로(Re-run이 아닌 새 run)부터 적용됩니다.

---

## 2. Re-run은 예전 워크플로를 씀

**Re-run**은 **그 run이 처음 돌았을 때의 워크플로 파일**을 다시 사용합니다.  
그때는 아직 `permissions: contents: write`가 없었을 수 있어서, Re-run만 하면 403이 계속 날 수 있습니다.

- **해결**: Re-run 대신 **새 태그를 푸시**해서 **새 run**을 띄우세요.  
  - 예: `git tag v1.0.8` → `git push origin v1.0.8`  
  - 그러면 **지금 저장소에 있는** 워크플로(권한 포함)로 실행됩니다.

---

## 3. 요약

| 상황 | 조치 |
|------|------|
| 403이 계속 남음 | **Settings → Actions → General → Workflow permissions** 에서 **Read and write permissions** 로 변경 후 저장 |
| Re-run만 반복함 | 새 태그 푸시로 **새 run** 실행 (v1.0.8 등) |

위 두 가지를 모두 적용한 뒤, 새로 돌린 run에서 APK가 Release에 붙는지 확인하면 됩니다.
