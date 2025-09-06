# templatetags/custom_filters.py
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='highlight')
def highlight(text, query):
    if not query:
        return text
    
    if not text:
        return text
        
    text = str(text)
    query = str(query)
    
    # Escape special regex characters in query
    escaped_query = re.escape(query)
    
    # Create regex pattern for case-insensitive matching
    pattern = re.compile(f'({escaped_query})', re.IGNORECASE)
    
    # Replace matches with highlighted span
    highlighted = pattern.sub(r'<span class="highlight">\1</span>', text)
    
    return mark_safe(highlighted)