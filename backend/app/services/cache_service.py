import json
from redis import Redis
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        self.cache_ttl = 3600  # Cache responses for 1 hour

    async def get_response(self, query: str, platform: str) -> Optional[str]:
        """Retrieve cached response"""
        cache_key = self._generate_cache_key(query, platform)
        return self.redis.get(cache_key)

    async def store_response(self, query: str, platform: str, response: str):
        """Store response in cache"""
        cache_key = self._generate_cache_key(query, platform)
        self.redis.setex(
            cache_key,
            self.cache_ttl,
            response
        )

    def _generate_cache_key(self, query: str, platform: str) -> str:
        """Generate a cache key from query and platform"""
        # Normalize query by removing spaces and converting to lowercase
        normalized_query = query.lower().strip().replace(" ", "-")
        return f"chat:response:{platform.lower()}:{normalized_query}"