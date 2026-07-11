#!/usr/bin/env python3
"""Verify all infrastructure services are healthy."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings
import redis as redis_lib
import requests

def check_postgres():
    try:
        import asyncpg, asyncio
        async def _check():
            conn = await asyncpg.connect(settings.DATABASE_URL.replace('+asyncpg', ''))
            count = await conn.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='koptumbuh'")
            await conn.close()
            return count
        return asyncio.run(_check())
    except Exception as e: return f"ERROR: {e}"

def check_redis():
    try:
        r = redis_lib.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        r.set('health_check', 'ok', ex=10)
        return r.get('health_check') == b'ok'
    except Exception as e: return f"ERROR: {e}"

def check_minio():
    try:
        r = requests.get(f"http://{settings.MINIO_ENDPOINT}/minio/health/live", timeout=2)
        return r.status_code == 200
    except Exception as e: return f"ERROR: {e}"

def check_evolution():
    try:
        r = requests.get(f"{settings.EVOLUTION_API_URL}/", timeout=2)
        return r.status_code in (200, 404)  # Evolution returns 200 on /
    except Exception as e: return f"ERROR: {e}"

def check_gemini():
    if not settings.GEMINI_API_KEY: return "SKIPPED (no key)"
    try:
        from app.services.ai_service import parse_text_to_json
        import asyncio
        result = asyncio.run(parse_text_to_json("test"))
        return isinstance(result, dict)
    except Exception as e: return f"ERROR: {e}"

if __name__ == '__main__':
    checks = {
        'PostgreSQL (tables)': check_postgres(),
        'Redis': check_redis(),
        'MinIO': check_minio(),
        'Evolution API': check_evolution(),
        'Gemini API': check_gemini(),
    }
    all_ok = True
    for name, result in checks.items():
        status = 'OK' if result is True or (isinstance(result, int) and result > 0) else str(result)
        if status != 'OK': all_ok = False
        print(f'  {name}: {status}')
    print(f'\nOverall: {"ALL OK" if all_ok else "SOME FAILED"}')
    sys.exit(0 if all_ok else 1)
