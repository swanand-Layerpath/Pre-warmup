"""Email sender for pre-warm session links using SMTP."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("PRE_WARM_FROM_EMAIL", "team@layerpath.com")


async def send_pre_warm_email(
    to_email: str,
    invitee_name: str,
    meeting_time: str,
    session_url: str
) -> bool:
    """
    Send pre-warm link via SMTP.

    Args:
        to_email: Recipient email address
        invitee_name: Recipient name
        meeting_time: ISO 8601 formatted meeting time
        session_url: URL to Path AI chat session

    Returns:
        True if email sent successfully, False otherwise
    """

    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not set, skipping email send")
        logger.info(f"Would send email to {to_email} with link: {session_url}")
        return False

    # Parse and format meeting time
    try:
        meeting_dt = datetime.fromisoformat(meeting_time.replace("Z", "+00:00"))
        meeting_formatted = meeting_dt.strftime('%B %d at %I:%M %p')
    except Exception as e:
        logger.warning(f"Failed to parse meeting time: {e}")
        meeting_formatted = meeting_time

    # Build email HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
        <div style="background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h2 style="color: #111827; margin-top: 0;">Hi {invitee_name}! 👋</h2>

            <p style="color: #374151; font-size: 16px; line-height: 1.6;">
                Thanks for booking time with us on <strong>{meeting_formatted}</strong>.
            </p>

            <p style="color: #374151; font-size: 16px; line-height: 1.6;">
                To make our call more productive, could you take 2-3 minutes for a quick voice chat with our AI assistant?
            </p>

            <div style="margin: 30px 0; text-align: center;">
                <a href="{session_url}"
                   style="background: #2563eb; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 6px; display: inline-block;
                          font-weight: 500; font-size: 16px;">
                    🎙️ Join Voice Call →
                </a>
            </div>

            <p style="color: #6b7280; font-size: 14px; line-height: 1.6;">
                <strong>What to expect:</strong> Click the button above to join a short voice call (works in your browser, no download needed).
                Our AI will ask a few quick questions to help us understand your needs and show up prepared.
            </p>

            <p style="color: #374151; font-size: 16px; line-height: 1.6; margin-top: 30px;">
                See you soon!<br>
                <strong>The Layerpath Team</strong>
            </p>
        </div>

        <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
            <p>If the button doesn't work, copy and paste this link:</p>
            <p style="word-break: break-all;">{session_url}</p>
        </div>
    </body>
    </html>
    """

    # Plain text version
    text_content = f"""
Hi {invitee_name}!

Thanks for booking time with us on {meeting_formatted}.

To make our call more productive, could you take 2-3 minutes for a quick voice chat with our AI assistant?

Join Voice Call: {session_url}

What to expect: Click the link above to join a short voice call (works in your browser, no download needed). Our AI will ask a few quick questions to help us understand your needs and show up prepared.

See you soon!
The Layerpath Team
    """

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Quick prep before our call on {meeting_formatted}"
        msg['From'] = f"Layerpath <{FROM_EMAIL}>"
        msg['To'] = f"{invitee_name} <{to_email}>"

        # Attach plain text and HTML versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Connect to SMTP server and send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()  # Enable TLS encryption
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Successfully sent pre-warm email to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending email via SMTP: {e}")
        return False
