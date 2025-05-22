from django.core.cache import cache
import logging
import time
import hashlib
import json

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Centralized cache management system for the football scores application
    Uses Django's cache backend (configurable to use memcached, redis, etc.)
    """
    
    # Cache timeouts (in seconds)
    CACHE_TIMEOUT_SHORT = 60 * 5        # 5 minutes for rapidly changing data
    CACHE_TIMEOUT_MEDIUM = 60 * 60      # 1 hour for semi-static data
    CACHE_TIMEOUT_LONG = 60 * 60 * 24   # 24 hours for rarely changing data
    
    @staticmethod
    def _generate_cache_key(prefix, identifier):
        """Generate a standardized cache key"""
        return f"{prefix}:{identifier}"
    
    @staticmethod
    def _hash_complex_key(data):
        """Create a hash for complex data structures to use as part of cache keys"""
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data, sort_keys=True)
        return hashlib.md5(str(data).encode()).hexdigest()
    
    @classmethod
    def cache_match_data(cls, match_id, data):
        """Cache preprocessed match data"""
        key = cls._generate_cache_key('match', match_id)
        cache.set(key, data, cls.CACHE_TIMEOUT_MEDIUM)
        logger.debug(f"Cached match data: {key}")
        return True
    
    @classmethod
    def get_match_data(cls, match_id):
        """Get preprocessed match data from cache"""
        key = cls._generate_cache_key('match', match_id)
        data = cache.get(key)
        logger.debug(f"Cache {'hit' if data else 'miss'} for match data: {key}")
        return data
    
    @classmethod
    def cache_timeline_events(cls, match_id, events):
        """Cache timeline events for a match"""
        key = cls._generate_cache_key('timeline', match_id)
        cache.set(key, events, cls.CACHE_TIMEOUT_MEDIUM)
        logger.debug(f"Cached timeline events: {key}")
        return True
    
    @classmethod
    def get_timeline_events(cls, match_id):
        """Get timeline events from cache"""
        key = cls._generate_cache_key('timeline', match_id)
        events = cache.get(key)
        logger.debug(f"Cache {'hit' if events else 'miss'} for timeline events: {key}")
        return events
    
    @classmethod
    def cache_match_stats(cls, match_id, stats):
        """Cache match statistics"""
        key = cls._generate_cache_key('stats', match_id)
        cache.set(key, stats, cls.CACHE_TIMEOUT_MEDIUM)
        logger.debug(f"Cached match stats: {key}")
        return True
    
    @classmethod
    def get_match_stats(cls, match_id):
        """Get match statistics from cache"""
        key = cls._generate_cache_key('stats', match_id)
        stats = cache.get(key)
        logger.debug(f"Cache {'hit' if stats else 'miss'} for match stats: {key}")
        return stats
    
    @classmethod
    def cache_team_form(cls, team_id, form_data):
        """Cache team form data"""
        key = cls._generate_cache_key('team_form', team_id)
        cache.set(key, form_data, cls.CACHE_TIMEOUT_SHORT)
        logger.debug(f"Cached team form: {key}")
        return True
    
    @classmethod
    def get_team_form(cls, team_id):
        """Get team form data from cache"""
        key = cls._generate_cache_key('team_form', team_id)
        form = cache.get(key)
        logger.debug(f"Cache {'hit' if form else 'miss'} for team form: {key}")
        return form
    
    @classmethod
    def invalidate_match_cache(cls, match_id):
        """Invalidate all cache entries related to a match"""
        prefixes = ['match', 'timeline', 'stats']
        for prefix in prefixes:
            key = cls._generate_cache_key(prefix, match_id)
            cache.delete(key)
        logger.debug(f"Invalidated cache for match: {match_id}")
        return True
    
    @classmethod
    def clear_all_caches(cls):
        """Clear all caches (use sparingly)"""
        cache.clear()
        logger.info("All caches cleared")
        return True