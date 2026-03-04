# 팀 전용 — Jetson 접속 정보 암호화 보관

**목적**: Jetson 서버 SSH 접속 정보를 암호화해 보관하고, 팀원만 필요할 때 복호화해 사용한다. **저장소·외부에 비밀번호가 노출되지 않도록 한다.**

---

## 1. 보관 위치 (저장소 제외)

- 암호화된 파일은 **`secrets/`** 폴더 또는 팀만 접근 가능한 **비공개 저장소/클라우드**에 둔다.
- `.gitignore`에 `secrets/`, `*.jetson.enc`, `*jetson*access*.txt`가 포함되어 있어 **실수로 커밋되지 않는다.**

---

## 2. 처음 한 번 — 암호화해서 보관하기

### 2.1 접속 정보를 평문 파일로 작성 (로컬에서만)

`secrets/jetson_access.txt` 같은 파일을 만들고 아래 형식으로 적는다.  
**(이 파일은 절대 저장소에 올리지 않고, 암호화 후 삭제한다.)**

```
host=100.80.178.45
user=upbit
password=여기에_실제_비밀번호
```

### 2.2 OpenSSL로 암호화

팀끼리만 아는 **암호화 비밀번호**를 정한 뒤, 아래를 실행한다.

```bash
# secrets 폴더 생성 (이미 있으면 생략)
mkdir -p secrets

# 암호화 (실행 후 프롬프트에서 암호 입력)
openssl enc -aes-256-cbc -salt -in secrets/jetson_access.txt -out secrets/jetson_access.enc

# 평문 파일 삭제
del secrets\jetson_access.txt
# (Linux/Mac: rm secrets/jetson_access.txt)
```

- `secrets/jetson_access.enc` 만 보관한다. 이 파일은 암호를 모르면 복호화할 수 없다.
- **암호화 비밀번호**는 팀 내부에서만 안전한 경로(비밀번호 관리자, 암호화된 메모 등)로 공유하고, 채팅·문서에 적지 않는다.

---

## 3. 필요할 때 — 복호화해서 사용하기

### 3.1 복호화 (일시적으로 평문 생성)

```bash
openssl enc -aes-256-cbc -d -in secrets/jetson_access.enc -out secrets/jetson_access.txt
# 프롬프트에서 암호화할 때 쓴 비밀번호 입력
```

### 3.2 SSH 접속

- `secrets/jetson_access.txt` 에서 host, user, password를 확인한 뒤:
  - `ssh user@host` 로 접속하고, 비밀번호 입력.
- 사용이 끝나면 **평문 파일 삭제**:
  - `del secrets\jetson_access.txt` (Windows) / `rm secrets/jetson_access.txt` (Linux/Mac)

### 3.3 (선택) 스크립트로 한 번에 접속

복호화 후 `ssh upbit@100.80.178.45` 로 접속하거나, 팀에서 쓰는 방식(예: SSH 키 등)으로 접속한다.  
비밀번호를 스크립트에 적지 말 것.

---

## 4. 팀 규칙

- **암호화된 파일(`.enc`)과 암호화 비밀번호**는 팀 내부에서만 공유한다.
- **평문 접속 정보**는 채팅·이메일·공개 문서에 붙여넣지 않는다.
- 저장소에는 `secrets/` 및 `*.jetson.enc` 가 올라가지 않도록 이미 `.gitignore`에 포함되어 있다.
