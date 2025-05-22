import time
import logging
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class RequestPerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to log request performance statistics
    """
    def process_request(self, request):
        request.start_time = time.time()
        
    def process_response(self, request, response):
        # Skip if start_time wasn't set (for some middleware requests)
        if not hasattr(request, 'start_time'):
            return response
        
        # Calculate request processing time
        duration = time.time() - request.start_time
        
        # Log performance data for slower requests
        if duration > 0.5:  # Log requests taking more than 500ms
            # Count database queries
            db_queries = len(connection.queries)
            
            logger.warning(
                f"Slow request: {request.method} {request.path} - "
                f"Time: {duration:.3f}s, DB Queries: {db_queries}"
            )
            
            # Log detailed query information for very slow requests
            if duration > 1.0:  # If request took more than 1 second
                queries_time = sum(float(q['time']) for q in connection.queries)
                logger.warning(f"Queries execution time: {queries_time:.3f}s")
                
                # Find and log slow queries
                slow_queries = [q for q in connection.queries if float(q['time']) > 0.1]
                if slow_queries:
                    for query in slow_queries:
                        logger.warning(f"Slow query ({query['time']}s): {query['sql'][:500]}")
        
        # Add performance information for admins
        if request.user and request.user.is_staff:
            if 'text/html' in response.get('Content-Type', ''):
                # Add X-Processing-Time header for admins
                response['X-Processing-Time'] = f"{duration:.3f}s"
                response['X-DB-Queries'] = str(len(connection.queries))
        
        return response


class CacheHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add cache control headers based on content type
    """
    def process_response(self, request, response):
        # Handle static files with long cache
        path = request.path_info.lower()
        
        # Define file types and cache times
        cache_settings = {
            # Static assets - cache for 30 days
            '.css': 2592000,
            '.js': 2592000,
            '.png': 2592000,
            '.jpg': 2592000,
            '.jpeg': 2592000,
            '.gif': 2592000,
            '.ico': 2592000,
            '.svg': 2592000,
            '.woff': 2592000,
            '.woff2': 2592000,
            '.ttf': 2592000,
            '.eot': 2592000,
            
            # HTML/JSON - short cache or no cache
            '.html': 0,
            '.json': 300,  # 5 minutes for JSON API responses
        }
        
        # Set cache headers based on file extension
        for ext, cache_time in cache_settings.items():
            if path.endswith(ext):
                if cache_time > 0:
                    response['Cache-Control'] = f'max-age={cache_time}, public'
                else:
                    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    response['Pragma'] = 'no-cache'
                    response['Expires'] = '0'
                break
        
        # For authenticated users, ensure HTML responses aren't cached
        if (request.user.is_authenticated and
            'text/html' in response.get('Content-Type', '') and
            'Cache-Control' not in response):
            response['Cache-Control'] = 'private, no-cache'
            
        return response
