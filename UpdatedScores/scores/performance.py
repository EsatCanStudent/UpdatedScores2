import time
import logging
import functools
from functools import wraps
from django.db import connection, reset_queries
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

def timing_decorator(func):
    """Decorator for timing function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        logger.info(f"Function {func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper

def caching_decorator(timeout=3600):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a unique cache key from the function name and arguments
            key_parts = [func.__name__]
            
            # Add all positional args to the key
            key_parts.extend([str(arg) for arg in args])
            
            # Add all keyword args to the key
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            
            # Join them to make the cache key
            cache_key = "funcache:" + "_".join(key_parts)
            
            # Try to get from cache
            result = cache.get(cache_key)
            
            # If not in cache, call the function and cache the result
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cache miss for {func.__name__} - stored with key {cache_key}")
            else:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                
            return result
        return wrapper
    return decorator

def query_debugger(func):
    """Decorator for logging database queries"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Only debug queries in debug mode
        if not settings.DEBUG:
            return func(*args, **kwargs)
        
        reset_queries()
        start_queries = len(connection.queries)
        start_time = time.time()
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_queries = len(connection.queries)
        
        query_time = sum(float(q['time']) for q in connection.queries)
        logger.info(f"Function: {func.__name__}")
        logger.info(f"Number of Queries: {end_queries - start_queries}")
        logger.info(f"Total time for queries: {query_time:.4f}s")
        logger.info(f"Total execution time: {(end_time - start_time):.4f}s")
        
        return result
    return wrapper

def memory_usage_decorator(func):
    """Decorator for tracking memory usage of a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            import psutil
            import os
            
            # Get current process
            process = psutil.Process(os.getpid())
            
            # Get memory info before function execution
            start_memory = process.memory_info().rss / 1024 / 1024  # in MB
            
            result = func(*args, **kwargs)
            
            # Get memory info after function execution
            end_memory = process.memory_info().rss / 1024 / 1024  # in MB
            
            logger.info(f"Function {func.__name__} - Memory Usage:")
            logger.info(f"  Before: {start_memory:.2f} MB")
            logger.info(f"  After: {end_memory:.2f} MB")
            logger.info(f"  Difference: {end_memory - start_memory:.2f} MB")
            
            return result
        except ImportError:
            logger.warning("psutil module not installed, memory tracking disabled")
            return func(*args, **kwargs)
    
    return wrapper
