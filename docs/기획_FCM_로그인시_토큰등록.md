# 배짱이 v1.0 — FCM 토큰 등록 (모든 로그인 경로)

**저작자**: 차리 (challychoi@me.com)

## 목적
이메일·구글·카카오 로그인 성공 시에도 FCM 토큰을 서버에 등록하여, **어떤 로그인 방식**을 써도 푸시 수신이 일관되게 동작하도록 한다.

## 현황 (보완 전)
- **생체인증 로그인**: `loginWithBiometric()` 성공 시 `_notification.registerOnLogin()` 호출 → FCM 토큰 서버 등록됨.
- **이메일 / 구글 / 카카오 로그인**: `_onLoginSuccess()`만 호출되고, FCM 토큰 등록 호출 없음 → 해당 경로로 로그인한 사용자는 푸시를 받지 못할 수 있음.

## 요구사항
1. **이메일 로그인** (`login()`) 성공 시 → FCM 토큰 서버 등록.
2. **구글 로그인** (`loginGoogle()`) 성공 시 → FCM 토큰 서버 등록.
3. **카카오 로그인** (`loginKakao()`) 성공 시 → FCM 토큰 서버 등록.
4. **생체인증 로그인** (`loginWithBiometric()`) — 기존대로 성공 시 FCM 토큰 등록 유지.

## 구현 방향
- `AuthNotifier._onLoginSuccess()` 에서 **토큰 저장·상태 갱신·생체 토큰 저장** 후, `NotificationService.registerOnLogin()` 호출 추가.
- `_onLoginSuccess`는 `login()`, `loginGoogle()`, `loginKakao()` 세 경로에서만 호출되므로, 한 곳만 수정하면 세 로그인 모두에 적용됨.
- `loginWithBiometric()`은 `_onLoginSuccess`를 쓰지 않고 별도 플로우이므로, 기존처럼 해당 메서드 내에서 `registerOnLogin()` 호출 유지.

## 작업 지시 (개발관)
1. `AuthNotifier` 생성자에 `NotificationService _notification` 인자 추가 (이미 provider에서 전달 중이면 필드만 추가).
2. `_onLoginSuccess()` 마지막에 `await _notification.registerOnLogin();` 호출 추가.
3. (선택) 실패해도 로그인 자체는 성공으로 두고, 푸시만 미등록될 수 있도록 `registerOnLogin()` 내부는 기존대로 예외 시 로그만 남기고 무시.

## 검증 (검증관)
- 이메일 로그인 성공 후 서버에 FCM 토큰이 등록되는지(또는 `PUT /api/v1/auth/me/fcm-token` 호출 여부) 확인.
- 구글·카카오 로그인 성공 후 동일 동작 확인.
- 생체인증 로그인 시 기존과 동일하게 FCM 토큰 등록되는지 확인.

## 완료 기준
- 위 네 가지 로그인 경로(이메일·구글·카카오·생체) 모두 로그인 성공 시 FCM 토큰 서버 등록이 이루어짐.
- 123.txt 작업지시서에 본 항목 반영 및 [완료!] 표기.
