"""Send email over SMTP (stdlib: works with Brevo, Gmail app passwords, Mailgun, SES SMTP...).
Not configured = disabled: callers fall back to in-app delivery."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("app.email")


class EmailError(Exception):
    pass


def email_enabled() -> bool:
    s = get_settings()
    return bool(s.smtp_host and s.email_from)


def send_email(to: str, subject: str, text: str, html: str | None = None, headers: dict | None = None) -> bool:
    """True if sent, False if email is disabled. Raises EmailError if the provider rejects it."""
    s = get_settings()
    if not email_enabled():
        log.info("email disabled (no SMTP_HOST/EMAIL_FROM); not sending '%s'", subject)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.email_from, to, subject
    for k, v in (headers or {}).items():
        msg[k] = v
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        ctx = ssl.create_default_context()
        if s.smtp_port == 465:
            with smtplib.SMTP_SSL(s.smtp_host, s.smtp_port, timeout=15, context=ctx) as smtp:
                _login_send(smtp, msg)
        else:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
                smtp.starttls(context=ctx)
                _login_send(smtp, msg)
    except (smtplib.SMTPException, OSError) as e:
        raise EmailError(str(e)) from e
    return True


def _login_send(smtp: smtplib.SMTP, msg: EmailMessage) -> None:
    s = get_settings()
    if s.smtp_user:
        smtp.login(s.smtp_user, s.smtp_password)
    smtp.send_message(msg)
