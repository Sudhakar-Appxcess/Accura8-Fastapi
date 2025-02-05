import random
import string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from logzero import logger
from app.config import settings

ENVIRONMENT = settings.ENVIRONMENT

def generate_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))

def get_email_template(verification_code: str) -> str:

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                text-align: center;
                padding: 20px 0;
                border-bottom: 2px solid #f0f0f0;
            }}
            .content {{
                padding: 20px 0;
            }}
            .verification-code {{
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                color: #495057;
                font-size: 24px;
                font-weight: bold;
                letter-spacing: 2px;
                margin: 20px 0;
                padding: 15px;
                text-align: center;
            }}
            .footer {{
                text-align: center;
                padding-top: 20px;
                border-top: 2px solid #f0f0f0;
                color: #6c757d;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Email Verification</h1>
            </div>
            <div class="content">
                <p>Hello!</p>
                <p>Thank you for registering. To complete your registration, please use the verification code below:</p>
                <div class="verification-code">
                    {verification_code}
                </div>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't request this verification, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply.</p>
                <p>&copy; {settings.COMPANY_NAME if hasattr(settings, 'COMPANY_NAME') else '2025'} All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

async def send_verification_email(email: str, verification_code: str):
    """
    Sends a verification email using SendGrid
    """
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject='Verify Your Email',
            html_content=get_email_template(verification_code)
        )

        # In development, just log the code instead of sending email
        if ENVIRONMENT != "Production":
            logger.info(f"Development environment - Verification code for {email}: {verification_code}")
        else:
            sg.send(message)
            logger.info(f"Verification email sent to: {email}")
            
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        raise