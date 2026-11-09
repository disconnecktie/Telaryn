"""Deliver one-time invitation links without persisting or logging bearer tokens."""

from dataclasses import dataclass
from html import escape
from urllib.parse import quote, urlparse

from app.core.config import settings


class InvitationDeliveryUnavailable(RuntimeError):
    """A safe, non-provider-specific delivery failure."""


@dataclass(frozen=True)
class DeliveryResult:
    provider: str
    message_id: str | None = None


def invitation_message(*, recipient_name: str, link: str) -> dict[str, str]:
    """Build the branded, accessible invitation in HTML and plain text."""
    safe_name = escape(recipient_name)
    safe_link = escape(link, quote=True)
    parsed_link = urlparse(link)
    guide_link = f"{parsed_link.scheme}://{parsed_link.netloc}/#/getting-started"
    safe_guide_link = escape(guide_link, quote=True)
    plain_text = (
        f"Hello {recipient_name},\n\n"
        "Your request for access to Telaryn has been approved.\n\n"
        "Create your private workspace:\n"
        f"{link}\n\n"
        "This private link expires in 72 hours and can only be used once. "
        "If you did not request access to Telaryn, you can safely ignore this message.\n\n"
        "See how Telaryn works:\n"
        f"{guide_link}\n\n"
        "Use Telaryn like an app on iPhone:\n"
        "1. Open https://telaryn.app in Safari.\n"
        "2. Tap the Share button.\n"
        "3. Choose Add to Home Screen, then tap Add.\n\n"
        "Use Telaryn like an app on Android:\n"
        "1. Open https://telaryn.app in Chrome.\n"
        "2. Tap Chrome's three-dot menu.\n"
        "3. Choose Install app or Add to Home screen, then confirm.\n\n"
        "Telaryn will open from your Home Screen like an app. Native iPhone and "
        "Android apps are planned for a future release.\n\n"
        "Need help? Contact support@telaryn.app.\n\n"
        "Telaryn\nEvery action has a purpose."
    )
    html = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#f1f4f8;color:#162033;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#f1f4f8;">
      <tr>
        <td align="center" style="padding:32px 16px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border:1px solid #d9e1ea;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px;background:#101d31;color:#ffffff;">
                <div style="font-size:13px;font-weight:700;letter-spacing:0.18em;">TELARYN</div>
                <div style="margin-top:10px;color:#aebed1;font-size:14px;">Every action has a purpose.</div>
              </td>
            </tr>
            <tr>
              <td style="padding:36px 32px 32px;">
                <p style="margin:0 0 14px;color:#536277;font-size:16px;line-height:1.6;">Hello {safe_name},</p>
                <h1 style="margin:0 0 16px;color:#101d31;font-size:28px;line-height:1.2;">Your workspace is ready.</h1>
                <p style="margin:0 0 28px;color:#39485d;font-size:16px;line-height:1.65;">Your request for access to Telaryn has been approved. Create your private workspace to start turning your work into clear, purposeful action.</p>
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="border-radius:10px;background:#101d31;">
                      <a href="{safe_link}" style="display:inline-block;padding:14px 22px;color:#ffffff;font-size:16px;font-weight:700;text-decoration:none;">Create your workspace</a>
                    </td>
                  </tr>
                </table>
                <p style="margin:22px 0 0;color:#66758a;font-size:14px;line-height:1.6;">This private link expires in 72 hours and can only be used once.</p>
                <div style="margin:30px 0 24px;border-top:1px solid #e1e7ee;"></div>
                <p style="margin:0 0 8px;color:#66758a;font-size:13px;line-height:1.6;">Button not working? Copy and paste this address into your browser:</p>
                <p style="margin:0;word-break:break-all;font-size:13px;line-height:1.6;"><a href="{safe_link}" style="color:#315f9d;">{safe_link}</a></p>
                <p style="margin:24px 0 0;color:#536277;font-size:14px;line-height:1.6;">New to Telaryn? <a href="{safe_guide_link}" style="color:#315f9d;font-weight:700;">See how it works</a> before you begin.</p>
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:28px;border:1px solid #cbd8e6;border-radius:12px;background:#f4f8fc;">
                  <tr>
                    <td style="padding:20px 22px;">
                      <div style="color:#315f9d;font-size:11px;font-weight:700;letter-spacing:0.12em;">USE TELARYN LIKE AN APP</div>
                      <h2 style="margin:7px 0 14px;color:#101d31;font-size:19px;line-height:1.3;">Add Telaryn to your Home Screen</h2>
                      <div style="margin-bottom:5px;color:#101d31;font-size:14px;font-weight:700;">iPhone · Safari</div>
                      <ol style="margin:0;padding-left:20px;color:#39485d;font-size:14px;line-height:1.7;">
                        <li>Open <a href="https://telaryn.app" style="color:#315f9d;">telaryn.app</a> in Safari.</li>
                        <li>Tap the <strong>Share</strong> button.</li>
                        <li>Choose <strong>Add to Home Screen</strong>, then tap <strong>Add</strong>.</li>
                      </ol>
                      <div style="margin:16px 0 5px;padding-top:14px;border-top:1px solid #d7e1ec;color:#101d31;font-size:14px;font-weight:700;">Android · Chrome</div>
                      <ol style="margin:0;padding-left:20px;color:#39485d;font-size:14px;line-height:1.7;">
                        <li>Open <a href="https://telaryn.app" style="color:#315f9d;">telaryn.app</a> in Chrome.</li>
                        <li>Tap Chrome’s <strong>three-dot menu</strong>.</li>
                        <li>Choose <strong>Install app</strong> or <strong>Add to Home screen</strong>, then confirm.</li>
                      </ol>
                      <p style="margin:13px 0 0;color:#66758a;font-size:12px;line-height:1.55;">Telaryn will open from your Home Screen like an app. Native iPhone and Android apps are planned for a future release.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:22px 32px;background:#f7f9fb;color:#69788c;font-size:12px;line-height:1.6;">
                <p style="margin:0 0 6px;">If you did not request access to Telaryn, you can safely ignore this message.</p>
                <p style="margin:0;">Need help? <a href="mailto:support@telaryn.app" style="color:#315f9d;">support@telaryn.app</a></p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
    return {
        "subject": "Your Telaryn workspace is ready",
        "plainText": plain_text,
        "html": html,
    }


def activation_url(token: str) -> str:
    base = (settings.public_app_url or "").strip().rstrip("/")
    if settings.environment == "development" and not base:
        base = next((value.strip().rstrip("/") for value in settings.frontend_origins.split(",") if value.strip()), "")
    parsed = urlparse(base)
    if not base or not parsed.netloc or parsed.scheme not in ({"http", "https"} if settings.environment == "development" else {"https"}):
        raise InvitationDeliveryUnavailable("Invitation delivery is not configured.")
    return f"{base}/#/accept-invitation?token={quote(token, safe='')}"


def deliver_invitation(*, recipient_email: str, recipient_name: str, token: str) -> tuple[DeliveryResult, str | None]:
    """Return a manual link only in development; otherwise send through Azure."""
    link = activation_url(token)
    provider = settings.invitation_delivery_provider
    if provider == "manual":
        if settings.environment != "development":
            raise InvitationDeliveryUnavailable("Invitation delivery is not configured.")
        return DeliveryResult(provider="manual"), link
    if provider != "azure":
        raise InvitationDeliveryUnavailable("Invitation delivery is not configured.")
    endpoint = (settings.azure_communication_email_endpoint or "").strip()
    sender = (settings.azure_communication_email_sender or "").strip()
    if not endpoint.startswith("https://") or not sender:
        raise InvitationDeliveryUnavailable("Invitation delivery is not configured.")
    try:
        from azure.communication.email import EmailClient
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential(
            managed_identity_client_id=settings.azure_managed_identity_client_id
        )
        client = EmailClient(endpoint, credential)
        message = {
            "senderAddress": sender,
            "recipients": {"to": [{"address": recipient_email, "displayName": recipient_name}]},
            "content": invitation_message(recipient_name=recipient_name, link=link),
        }
        result = client.begin_send(message).result(
            timeout=settings.invitation_delivery_timeout_seconds
        )
        message_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        return DeliveryResult(provider="azure", message_id=str(message_id) if message_id else None), None
    except InvitationDeliveryUnavailable:
        raise
    except Exception as exc:
        raise InvitationDeliveryUnavailable("Telaryn could not deliver the invitation.") from exc
