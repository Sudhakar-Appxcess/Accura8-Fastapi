from app.config import settings;
import httpx
from logzero import logger

# async def verify_recaptcha(token: str) -> bool:
#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 'https://www.google.com/recaptcha/api/siteverify',
#                 data={
#                     'secret': settings.RECAPTCHA_SECRET_KEY, 
#                     'response': token
#                 }
#             )
#             result = response.json()
#             logger.info("Response of reCaptcha: %s", result)
#             # Log the full response for debugging
#             logger.debug("Full response: %s", response.text)
#             return result.get('success', False)
#     except Exception as e:
#         logger.error("Error verifying reCAPTCHA: %s", str(e))
#         return False


async def verify_recaptcha(token: str) -> bool:
    try:
        secret_key = settings.RECAPTCHA_SECRET_KEY
        logger.debug("Secret key from settings: %s", secret_key)  # Check if key is loaded
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={
                    'secret': secret_key,
                    'response': token
                }
            )
            result = response.json()
            logger.info("Response of reCaptcha: %s", result)
            return result.get('success', False)
    except AttributeError:
        logger.error("RECAPTCHA_SECRET_KEY not found in settings")
        return False
    except Exception as e:
        logger.error("Error: %s", str(e))
        return False