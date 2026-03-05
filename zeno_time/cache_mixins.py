"""
Mixin for caching list() responses on read-often API endpoints.
Uses Django cache with per-user key so responses are cached for a short TTL.
Also sets Cache-Control header for client/proxy caching where appropriate.
"""
import hashlib
from django.conf import settings
from django.core.cache import cache
from rest_framework.response import Response


def _make_list_cache_key(request):
    """Build cache key: user + path + sorted query string (GET only)."""
    user_id = getattr(request.user, 'id', None) or 'anon'
    path = request.path or ''
    qs = request.META.get('QUERY_STRING', '') or ''
    # Normalize query string order so same params = same key
    parts = sorted(qs.split('&')) if qs else []
    qs_normalized = '&'.join(p for p in parts if p)
    raw = f"api:list:{user_id}:{path}:{qs_normalized}"
    return hashlib.md5(raw.encode()).hexdigest()


class CacheListResponseMixin:
    """
    Mixin for ViewSets that expose list().
    Caches list response for CACHE_TIMEOUT_API seconds (per user + path + query).
    Set cache_list = True on the view class to enable; default True for GET list.
    """
    cache_list = True
    cache_timeout = getattr(settings, 'CACHE_TIMEOUT_API', 60)

    def list(self, request, *args, **kwargs):
        if not self.cache_list or request.method != 'GET':
            return super().list(request, *args, **kwargs)
        cache_key = _make_list_cache_key(request)
        cached = cache.get(cache_key)
        if cached is not None:
            response = Response(cached)
            response['Cache-Control'] = 'private, max-age=%d' % min(self.cache_timeout, 60)
            return response
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200 and hasattr(response, 'data'):
            cache.set(cache_key, response.data, self.cache_timeout)
            response['Cache-Control'] = 'private, max-age=%d' % min(self.cache_timeout, 60)
        return response
