# helpers/ip.py
import socket
import requests
from logzero import logger

def get_system_ip() -> str:
    """
    Get the system's public IP using a reliable IP lookup service
    """
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        logger.error(f"Error getting public IP: {str(e)}")
        # Fallback to hostname-based IP
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception as e:
            logger.error(f"Error getting hostname IP: {str(e)}")
            return "127.0.0.1"  # Return localhost if all fails