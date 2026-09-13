from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings


@lru_cache
def get_supabase() -> Client:
    """service_role 키로 접근하는 백엔드 전용 클라이언트 — RLS를 우회해서 쓴다."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
