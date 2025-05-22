from django import template
from django.core.cache import cache
from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter
import time
import hashlib
import logging

register = template.Library()
logger = logging.getLogger(__name__)

@register.simple_tag(takes_context=True)
def cached_include(context, template_name, timeout=3600, key_prefix=''):
    """
    Cache the template inclusion for specified time
    Usage: {% cached_include 'path/to/template.html' timeout=3600 key_prefix='uniquekey' %}
    """
    # Generate cache key
    cache_key = f"cached_include:{key_prefix}:{template_name}"
    
    # Add request path if it exists
    if 'request' in context:
        path = context['request'].path
        cache_key += f":{path}"
    
    # Check cache
    cached_content = cache.get(cache_key)
    if cached_content is not None:
        return mark_safe(cached_content)
    
    # Render template
    t = template.loader.get_template(template_name)
    content = t.render(context.flatten())
    
    # Store in cache
    cache.set(cache_key, content, timeout)
    return mark_safe(content)

@register.simple_tag
def cache_bust(path):
    """
    Add a cache-busting parameter to static file URLs
    Usage: {% cache_bust '/static/css/styles.css' %}
    Returns: /static/css/styles.css?v=123456
    """
    return f"{path}?v={int(time.time())}"

@register.filter(name='cache_key_from')
@stringfilter
def cache_key_from(value, prefix='template'):
    """
    Generate a cache key from a string value
    Usage: {{ some_string|cache_key_from:'prefix' }}
    """
    return f"{prefix}:{hashlib.md5(value.encode()).hexdigest()[:12]}"

class CacheNode(template.Node):
    def __init__(self, nodelist, expire_time, cache_key):
        self.nodelist = nodelist
        self.expire_time = template.Variable(expire_time)
        self.cache_key = template.Variable(cache_key)

    def render(self, context):
        try:
            expire_time = self.expire_time.resolve(context)
            cache_key = self.cache_key.resolve(context)
            
            # Try to get content from cache
            content = cache.get(cache_key)
            
            # If not in cache, render and cache
            if content is None:
                content = self.nodelist.render(context)
                cache.set(cache_key, content, expire_time)
                logger.debug(f"Cache miss: {cache_key}")
            else:
                logger.debug(f"Cache hit: {cache_key}")
                
            return content
        except template.VariableDoesNotExist:
            return ''

@register.tag('cacheable')
def do_cache(parser, token):
    """
    Custom cache tag allowing for variable cache keys and times
    {% cacheable 3600 "unique_key_name" %}
        ... expensive template content ...
    {% endcacheable %}
    """
    bits = token.split_contents()
    if len(bits) != 3:
        raise template.TemplateSyntaxError("'%s' tag requires two arguments: expire time and cache key" % bits[0])
    
    nodelist = parser.parse(('endcacheable',))
    parser.delete_first_token()
    return CacheNode(nodelist, bits[1], bits[2])

@register.simple_tag(takes_context=True)
def cache_fragment(context, key, timeout=3600):
    """
    Start a cached fragment
    Usage: 
    {% cache_fragment "key_name" timeout=3600 as cache_hit %}
        ... expensive template content ...
    {% endcache_fragment %}
    """
    return cache.get(key) is not None

@register.simple_tag
def cache_set(key, content, timeout=3600):
    """
    Store content in cache
    Usage: {% cache_set "key_name" variable_content 3600 %}
    """
    cache.set(key, content, timeout)
    return ''

@register.simple_tag
def cache_get(key, default=''):
    """
    Get content from cache
    Usage: {% cache_get "key_name" default="Default text" %}
    """
    return cache.get(key, default)