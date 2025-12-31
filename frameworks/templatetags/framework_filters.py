"""
Template filters for formatting framework data
"""
from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()


@register.filter
def format_source_link(source):
    """
    Format source field as a clickable link if it contains a URL.
    Supports formats:
    - Plain URL: "https://example.com"
    - Text with URL: "Text|https://example.com"
    - Plain text: "Some text" (no link)
    """
    if not source:
        return mark_safe('<span style="color: var(--text-light);">—</span>')
    
    source = str(source).strip()
    
    # Check if source contains "|" separator (TEXT|URL format)
    if '|' in source:
        parts = source.split('|', 1)
        if len(parts) == 2:
            link_text = parts[0].strip()
            url = parts[1].strip()
            # Validate and normalize URL
            if url:
                # Normalize www. URLs
                if url.startswith('www.'):
                    url = 'https://' + url
                # Add https:// if URL doesn't have a scheme but looks like a domain
                elif not url.startswith(('http://', 'https://')):
                    # Check if it looks like a domain (contains dots and no spaces)
                    if '.' in url and ' ' not in url and not url.startswith('/'):
                        url = 'https://' + url
                
                # Validate it's a proper URL format
                if url.startswith(('http://', 'https://')):
                    from django.utils.html import escape
                    escaped_text = escape(link_text) if link_text else escape(url)
                    escaped_url = escape(url)
                    return mark_safe(
                        f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" '
                        f'style="color: var(--primary-color); text-decoration: underline;">{escaped_text}</a>'
                    )
            
            # Invalid URL format, just show text
            from django.utils.html import escape
            return mark_safe(f'<span>{escape(link_text)}</span>')
    
    # Check if source is a URL
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:[-\w.])+'  # domain name
        r'(?::[0-9]+)?'  # optional port
        r'(?:/(?:[\w/_.])*)?'  # optional path
        r'(?:\?(?:[\w&=%.])*)?'  # optional query string
        r'(?:#(?:[\w.])*)?$',  # optional fragment
        re.IGNORECASE
    )
    
    # Also check for www. URLs
    www_pattern = re.compile(r'^www\.[\w.-]+\.[\w]+', re.IGNORECASE)
    
    if url_pattern.match(source) or www_pattern.match(source):
        # It's a URL, make it a clickable link
        url = source
        if www_pattern.match(source):
            url = 'https://' + source
        # Use URL as link text, but truncate if too long
        display_text = url
        if len(display_text) > 60:
            display_text = display_text[:57] + '...'
        from django.utils.html import escape
        escaped_url = escape(url)
        escaped_text = escape(display_text)
        return mark_safe(
            f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" '
            f'style="color: var(--primary-color); text-decoration: underline;">{escaped_text}</a>'
        )
    
    # Not a URL, check if it contains a URL pattern somewhere
    # First, check for "Read (URL)" or "Text (URL)" pattern
    read_url_pattern = re.search(r'(\w+)\s*\(((?:https?://|www\.)[^\)]+)\)', source, re.IGNORECASE)
    if read_url_pattern:
        from django.utils.html import escape
        link_text = read_url_pattern.group(1).strip()  # "Read" or other text
        url = read_url_pattern.group(2).strip()  # The URL
        
        # Normalize URL
        if url.startswith('www.'):
            url = 'https://' + url
        
        # Remove closing parenthesis if it's part of the URL (shouldn't be, but handle it)
        url = url.rstrip(')')
        
        # Get text before the "Read (URL)" part
        before_text = source[:read_url_pattern.start()].strip()
        after_text = source[read_url_pattern.end():].strip()
        
        escaped_url = escape(url)
        escaped_link_text = escape(link_text)
        
        # Build the result: before_text + clickable link + after_text
        result_parts = []
        if before_text:
            result_parts.append(escape(before_text))
        
        result_parts.append(
            f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" '
            f'style="color: var(--primary-color); text-decoration: underline;">{escaped_link_text}</a>'
        )
        
        if after_text:
            result_parts.append(escape(after_text))
        
        return mark_safe(''.join(result_parts))
    
    # Check for URLs in text (not in parentheses format)
    url_in_text = re.search(r'https?://[^\s\)]+|www\.[^\s\)]+', source, re.IGNORECASE)
    if url_in_text:
        from django.utils.html import escape
        
        # Replace URLs in text with clickable links
        def replace_url(match):
            url = match.group(0)
            if url.startswith('www.'):
                url = 'https://' + url
            # Remove trailing closing parenthesis if present (shouldn't be part of URL)
            url = url.rstrip(')')
            escaped_url = escape(url)
            return f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" ' \
                   f'style="color: var(--primary-color); text-decoration: underline;">{escaped_url}</a>'
        
        # Split text by URLs, escape non-URL parts, and replace URLs with links
        parts = re.split(r'(https?://[^\s\)]+|www\.[^\s\)]+)', source, flags=re.IGNORECASE)
        result_parts = []
        for part in parts:
            if re.match(r'https?://[^\s\)]+|www\.[^\s\)]+', part, flags=re.IGNORECASE):
                # It's a URL, replace with link
                url = part.rstrip(')')  # Remove trailing parenthesis
                if url.startswith('www.'):
                    url = 'https://' + url
                escaped_url = escape(url)
                result_parts.append(
                    f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer" '
                    f'style="color: var(--primary-color); text-decoration: underline;">{escaped_url}</a>'
                )
            else:
                # Regular text, escape it
                result_parts.append(escape(part))
        
        return mark_safe(''.join(result_parts))
    
    # Plain text, no URL - check if it should link to source_detail view
    # Only if it doesn't look like a URL and is not empty
    if source and len(source) > 0:
        # For non-URL sources, link to source_detail view
        from django.utils.html import escape
        from urllib.parse import quote
        escaped_source = escape(source)
        quoted_source = quote(source)
        return mark_safe(
            f'<a href="/frameworks/source/?source={quoted_source}" '
            f'style="color: var(--primary-color);">{escaped_source}</a>'
        )
    
    return mark_safe('<span style="color: var(--text-light);">—</span>')
