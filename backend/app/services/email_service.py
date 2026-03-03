"""이메일 발송 (인증 코드, 회원가입 축하). SMTP 미설정 시 발송 건너뜀."""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def is_smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """이메일 발송. SMTP 미설정이면 False."""
    if not is_smtp_configured():
        return False
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
    body = f"""배짱이 회원가입을 위한 인증 번호입니다.

인증 번호: {code}

유효 시간은 10분입니다. 해당 번호를 앱에 입력해 주세요."""
    return send_email(to, subject, body)


def send_welcome_email(to: str, nickname: str) -> bool:
    subject = "[배짱이] 회원가입을 축하합니다"
    body = f"""{nickname}님, 배짱이에 가입해 주셔서 감사합니다.

이제 앱에서 로그인하여 업비트 자동매매 서비스를 이용하실 수 있습니다."""
    return send_email(to, subject, body)
