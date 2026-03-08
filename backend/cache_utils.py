import json

import extensions


def cache_get_json(key: str):
    """读取 JSON 缓存，Redis 不可用时直接回退为未命中。"""
    if extensions.redis_client is None:
        return None
    try:
        raw = extensions.redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set_json(key: str, value, ttl_seconds: int = 60):
    """写入 JSON 缓存，并附带过期时间。"""
    if extensions.redis_client is None:
        return False
    try:
        extensions.redis_client.setex(
            key,
            ttl_seconds,
            json.dumps(value, ensure_ascii=False),
        )
        return True
    except Exception:
        return False


def cache_delete(*keys: str):
    """删除指定缓存 key，后续写操作清缓存会复用这里。"""
    if extensions.redis_client is None or not keys:
        return 0
    try:
        return extensions.redis_client.delete(*keys)
    except Exception:
        return 0


def cache_delete_pattern(pattern: str):
    """按模式删除缓存 key，当前先用于课程列表这类小范围缓存失效。"""
    if extensions.redis_client is None:
        return 0
    try:
        keys = extensions.redis_client.keys(pattern)
        if not keys:
            return 0
        return extensions.redis_client.delete(*keys)
    except Exception:
        return 0
