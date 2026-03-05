"""이메일 발송 (인증 코드, 회원가입 축하). SMTP 미설정 시 발송 건너뜀."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.services.email_footer_constants import APP_INTRO, get_footer_plain


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _get_email_footer() -> tuple[str, str]:
    """발송 메일 하단에 붙일 앱 소개·문의 안내. (plain, html). 문구는 email_footer_constants 사용."""
    contact = (settings.APP_CONTACT_EMAIL or "").strip() or "baejjangi@example.com"
    plain = get_footer_plain(contact)
    html = (
        '<p style="margin-top:1.5em;color:#666;font-size:0.9em;">'
        "배짱이 앱은 엄청난 연구와 실제 테스트를 거쳐 안정성 있게 만들어진, "
        "최고의 엔진이 탑재된 좋은 앱입니다.<br>"
        "궁금한 점이 있으면 이메일을 보내 주세요: "
        f'<a href="mailto:{contact}">{contact}</a></p>'
    )
    return plain, html


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """이메일 발송. SMTP 미설정이면 False. 본문 뒤에 앱 소개·문의 푸터를 자동으로 붙입니다."""
    if not is_smtp_configured():
        return False
    footer_plain, footer_html = _get_email_footer()
    body_text = body_text.rstrip() + footer_plain
    if body_html:
        body_html = body_html.rstrip() + footer_html
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        port = settings.SMTP_PORT
        use_tls = port == 587
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, port) as server:
            if use_tls:
                server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to, msg.as_string())
        return True
    except Exception:
        return False


def send_verification_email(to: str, code: str) -> bool:
    subject = "[배짱이] 이메일 인증 번호"
    mins = settings.VERIFICATION_CODE_EXPIRE_MINUTES
    body = f"""배짱이 회원가입을 위한 인증 번호입니다.

인증 번호: {code}

유효 시간은 {mins}분입니다. 해당 번호를 앱에 입력해 주세요."""
    return send_email(to, subject, body)


def send_welcome_email(to: str, nickname: str) -> bool:
    subject = "[배짱이] 회원가입을 축하합니다"
    body = f"""{nickname}님, 배짱이에 가입해 주셔서 감사합니다.

이제 앱에서 로그인하여 업비트 자동매매 서비스를 이용하실 수 있습니다."""
    return send_email(to, subject, body)
