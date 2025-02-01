import os
import redis
import json
from typing import Any, Optional
from logzero import logger


class RedisHelper:
    """Helper class for Redis operations"""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        """Initialize Redis connection.

        Args:
            host: Redis host address
            port: Redis port number
            db: Redis database number
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            password=os.getenv('REDIS_PASSWORD')
        )

    def set(self, key: str, value: Any, expiry: Optional[int] = None,
            toJson=False) -> bool:
        """Set key-value pair in Redis.

        Args:
            key: Redis key
            value: Value to store
            expiry: Optional expiry time in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if toJson:
                try:
                    value = json.dumps(value)
                except Exception as e:
                    logger.exception(
                        f'Error Json Dumps in Redis Set: {str(e)}', e)
            self.redis_client.set(key, value)
            if expiry:
                self.redis_client.expire(key, expiry)
            return True
        except Exception as e:
            logger.exception(f'Error setting Redis key: {str(e)}', e)
            return False

    def get(self, key: str, toJson=False) -> Optional[str]:
        """Get value for key from Redis.

        Args:
            key: Redis key

        Returns:
            Optional[str]: Value if key exists, None otherwise
        """
        try:
            val = self.redis_client.get(key)
            try:
                if toJson:
                    val = json.loads(val)
            except Exception as e:
                logger.exception(
                    f'Error on Json loads in Redis Get: {str(e)}', e)
            return val
        except Exception as e:
            logger.exception(f'Error getting Redis key: {str(e)}', e)
            return None

    def delete(self, key: str) -> bool:
        """Delete key from Redis.

        Args:
            key: Redis key

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.exception(f'Error deleting Redis key: {str(e)}', e)
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis.

        Args:
            key: Redis key

        Returns:
            bool: True if key exists, False otherwise
        """
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.exception(f'Error checking Redis key: {str(e)}', e)
            return False

    def flush(self) -> bool:
        """Clear all keys from current database.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.redis_client.flushdb()
            return True
        except Exception as e:
            logger.exception(f'Error flushing Redis db: {str(e)}', e)
            return False
