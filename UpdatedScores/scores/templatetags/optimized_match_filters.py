from django import template
from django.db.models import QuerySet
from django.core.cache import cache
from datetime import timedelta
import json
import functools
import hashlib

register = template.Library()

# Expanded cache for various operations with per-key TTL values
class AdvancedCache:
    """Enhanced cache with per-key TTL control and expiration tracking"""
    _cache = {}  # Main cache store
    _expiry = {}  # Expiration timestamps
    _max_size = 1000  # Maximum cache entries
    _default_ttl = 3600  # 1 hour default TTL
    
    @classmethod
    def get(cls, key, default=None):
        """Get value from cache with expiration check"""
        # Check if key exists and is not expired
        if key in cls._cache and key in cls._expiry:
            import time
            if time.time() < cls._expiry[key]:
                return cls._cache[key]
            else:
                # Expired, remove from cache
                cls._remove(key)
        return default
    
    @classmethod
    def set(cls, key, value, ttl=None):
        """Set value in cache with TTL"""
        import time
        # Enforce maximum size
        if len(cls._cache) >= cls._max_size and key not in cls._cache:
            # Remove oldest entry
            oldest_key = min(cls._expiry, key=cls._expiry.get)
            cls._remove(oldest_key)
        
        # Set value and expiration
        cls._cache[key] = value
        cls._expiry[key] = time.time() + (ttl or cls._default_ttl)
        return True
    
    @classmethod
    def _remove(cls, key):
        """Remove an item from cache"""
        if key in cls._cache:
            del cls._cache[key]
        if key in cls._expiry:
            del cls._expiry[key]
    
    @classmethod
    def clear(cls):
        """Clear the entire cache"""
        cls._cache.clear()
        cls._expiry.clear()

# Initialize the advanced cache system
_ratings_cache = AdvancedCache()

# Decorator for caching filter results
def cached_filter(ttl=3600):
    """Cache decorator for template filters"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name and arguments
            key_parts = [func.__name__]
            for arg in args:
                # Handle different types of arguments for cache key generation
                if isinstance(arg, QuerySet):
                    key_parts.append(f"queryset:{arg.model.__name__}:{len(arg)}")
                elif isinstance(arg, (dict, list)):
                    # Use hash of JSON representation for complex objects
                    key_parts.append(hashlib.md5(json.dumps(arg, sort_keys=True).encode()).hexdigest())
                else:
                    key_parts.append(str(arg))
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = _ratings_cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Calculate result and cache it
            result = func(*args, **kwargs)
            _ratings_cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

@register.filter(name='filter')
@cached_filter(ttl=600)  # Cache for 10 minutes
def filter_by_attribute(queryset, filter_string):
    """
    Filter a queryset by attribute value
    Example usage: {{ queryset|filter:"status='LIVE'" }}
    """
    if not filter_string or not queryset:
        return queryset
    
    try:
        field, value = filter_string.split('=')
        field = field.strip()
        value = value.strip('\'"')
        
        filter_dict = {field: value}
        return queryset.filter(**filter_dict)
    except Exception:
        return queryset

@register.filter
def split_first(value, delimiter):
    """Split a string and return first part. Ex: '55%-45%' -> '55'"""
    if not value:
        return 50  # Default value
    try:
        return value.split(delimiter)[0]
    except (IndexError, AttributeError):
        return value

@register.filter
def split_second(value, delimiter):
    """Split a string and return second part. Ex: '55%-45%' -> '45'"""
    if not value:
        return 50  # Default value
    try:
        return value.split(delimiter)[1]
    except (IndexError, AttributeError):
        return value
        
@register.filter
def filter_by_result(matches, result_type):
    """Filter matches by result type: home_win, away_win, draw"""
    if not matches:
        return []
    
    filtered_matches = []
    for match in matches:
        if not match.score:
            continue
            
        try:
            home_goals, away_goals = map(int, match.score.split('-'))
            
            if result_type == 'home_win' and home_goals > away_goals:
                filtered_matches.append(match)
            elif result_type == 'away_win' and away_goals > home_goals:
                filtered_matches.append(match)
            elif result_type == 'draw' and home_goals == away_goals:
                filtered_matches.append(match)
        except (ValueError, IndexError):
            continue
            
    return filtered_matches

@register.filter
def get_percentage(value, total):
    """Calculate percentage of a value in a total. Ex: (3, 10) -> 30"""
    if not value or not total or total == 0:
        return 50  # Default value
    try:
        return int((float(value) / float(total)) * 100)
    except (ValueError, TypeError):
        return 50

@register.filter
def get_match_status(match, current_time):
    """Calculate match status: live, upcoming, completed"""
    if match.score:
        return "completed"
    
    match_start = match.match_date
    match_end = match_start + timedelta(hours=2)
    
    if match_start <= current_time <= match_end:
        return "live"
    elif current_time < match_start:
        return "upcoming"
    else:
        return "completed"
        
@register.filter
def get_form_color(form_letter):
    """Return color class based on form letter"""
    colors = {
        'W': 'success',
        'D': 'warning',
        'L': 'danger'
    }
    return colors.get(form_letter, 'secondary')
        
@register.filter
def parse_stats_for_chart(stats_json, stat_name):
    """
    Parse statistics from JSON for chart.js use
    Returns a comma-separated list of values to be used in JavaScript
    """
    if not stats_json or not isinstance(stats_json, dict):
        return "0, 0, 0, 0, 0, 0, 0"
    
    # Create a mapping of stats to their default values
    stats_map = {
        'possession': stats_json.get('possession', '50').replace('%', ''),
        'shots': stats_json.get('shots', 0),
        'shots_on_target': stats_json.get('shots_on_target', 0),
        'corners': stats_json.get('corners', 0),
        'fouls': stats_json.get('fouls', 0),
        'passes': stats_json.get('passes', 0),
        'pass_accuracy': stats_json.get('pass_accuracy', '70').replace('%', '')
    }
    
    try:
        # Convert values to appropriate types
        for key in ['possession', 'pass_accuracy']:
            if key in stats_map:
                stats_map[key] = float(stats_map[key])
        
        for key in ['shots', 'shots_on_target', 'corners', 'fouls', 'passes']:
            if key in stats_map:
                stats_map[key] = int(stats_map[key])
        
        values = [stats_map['possession'], stats_map['shots'], stats_map['shots_on_target'], 
                 stats_map['corners'], stats_map['fouls'], stats_map['passes'], 
                 stats_map['pass_accuracy']]
        
        return ', '.join(str(v) for v in values)
    except (ValueError, AttributeError):
        return "0, 0, 0, 0, 0, 0, 0"

@register.filter
@cached_filter()
def normalize_rating(rating, max_value=10):
    """Normalize a rating value to a percentage (0-100) based on max_value"""
    if not rating:
        return 0
    
    try:
        rating_float = float(rating)
        return int((rating_float / max_value) * 100)
    except (ValueError, TypeError):
        return 0

@register.filter
@cached_filter()
def get_rating_class(rating):
    """Return a CSS class based on player rating"""
    if not rating:
        return 'rating-average'
    
    try:
        rating_float = float(rating)
        if rating_float >= 8:
            return 'rating-high'
        elif rating_float >= 6:
            return 'rating-mid'
        else:
            return 'rating-low'
    except (ValueError, TypeError):
        return 'rating-average'

@register.filter
@cached_filter()
def process_player_ratings(player_ratings):
    """Process player ratings for a team into a list of dictionaries with name, rating, and rating class"""
    if not player_ratings:
        return []
    
    result = []
    try:
        for player, rating in player_ratings.items():
            rating_class = get_rating_class(rating)
            result.append({
                'name': player,
                'rating': rating,
                'rating_class': rating_class
            })
        return result
    except (AttributeError, ValueError, TypeError):
        return []

@register.filter
def get_h2h_percentage(home, away):
    """Calculate percentage for head-to-head bar visualization"""
    if not home and not away:
        return 50
    
    try:
        home_int = int(home)
        away_int = int(away)
        total = home_int + away_int
        
        if total == 0:
            return 50
            
        return int((home_int / total) * 100)
    except (ValueError, TypeError, ZeroDivisionError):
        return 50

# Pre-compute exception for jsonify
_json_dumps_error = "Error parsing JSON"

@register.filter
def jsonify(data):
    """Convert a Python object to a JSON string for use in JavaScript"""
    if data is None:
        return '{}'
    
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return _json_dumps_error

@register.filter
def get_events_for_timeline(events):
    """Process events for the match timeline visualization"""
    if not events:
        return []
        
    result = []
    for event in events:
        if hasattr(event, 'event_type') and event.event_type in ('GOAL', 'YELLOW', 'RED'):
            # Determine team (home or away)
            team = 'unknown'
            player_name = 'Unknown'
            
            if hasattr(event, 'player') and event.player:
                team = 'home' if event.player.team == event.match.home_team else 'away'
                player_name = event.player.name
                
            event_data = {
                'minute': event.minute,
                'type': event.event_type,
                'team': team,
                'player': player_name,
                'description': event.description
            }
            result.append(event_data)
            
    return result

# Define a small cache for formatted minutes
_minutes_cache = {}

@register.filter
def format_minutes(minutes):
    """Format minutes (like 90+)"""
    if not minutes:
        return "0'"
        
    # Check cache first
    if minutes in _minutes_cache:
        return _minutes_cache[minutes]
        
    try:
        min_val = int(minutes)
        if min_val > 90:
            result = "90+'"
        else:
            result = f"{min_val}'"
            
        # Store in cache
        _minutes_cache[minutes] = result
        return result
    except:
        result = f"{minutes}'"
        # Store in cache
        _minutes_cache[minutes] = result
        return result
