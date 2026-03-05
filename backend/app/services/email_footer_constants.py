"""이메일 푸터 문구 단일화. app.services.email_service 및 CLI(baejjangi test mail)에서 사용."""

APP_INTRO = (
    "배짱이 앱은 엄청난 연구와 실제 테스트를 거쳐 안정성 있게 만들어진, "
    "최고의 엔진이 탑재된 좋은 앱입니다.\n"
    "궁금한 점이 있으면 이메일을 보내 주세요: "
)


def get_footer_plain(contact_email: str) -> str:
    """문의 메일 주소를 받아 plain 텍스트 푸터 반환."""
    contact = (contact_email or "").strip() or "baejjangi@example.com"
    return "\n\n---\n" + APP_INTRO + contact
