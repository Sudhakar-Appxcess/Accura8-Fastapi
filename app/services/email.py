
# helpers/email.py
import random
import string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from logzero import logger
from app.config import settings

ENVIRONMENT=settings.ENVIRONMENT;

def generate_verification_code() -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

async def send_verification_email(email: str, verification_code: str):
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject='Verify Your Email',
            html_content=f'Your verification code is: {verification_code}'
        )
        
        if ENVIRONMENT != "Production":
            logger.info(f"Development environment - Verification code for {email}: {verification_code}")
        else:
            sg.send(message)
            logger.info(f"Verification email sent to: {email}")
            
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        raise  