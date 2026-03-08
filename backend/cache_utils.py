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


def cache_ttl(key: str):
    """读取缓存剩余秒数，Redis 不可用或键不存在时统一返回 0。"""
    if extensions.redis_client is None:
        return 0
    try:
        ttl = extensions.redis_client.ttl(key)
        return ttl if ttl and ttl > 0 else 0
    except Exception:
        return 0


def rate_limit_state(key: str, limit: int):
    """读取当前限流状态，不主动增加计数。"""
    if extensions.redis_client is None:
        return {"allowed": True, "count": 0, "retry_after": 0}
    try:
        raw = extensions.redis_client.get(key)
        count = int(raw) if raw else 0
        ttl = cache_ttl(key)
        return {
            "allowed": count <= limit,
            "count": count,
            "retry_after": ttl if count > limit else 0,
        }
    except Exception:
        return {"allowed": True, "count": 0, "retry_after": 0}


def rate_limit_record_failure(key: str, window_seconds: int):
    """记录一次失败尝试，并保持失败窗口过期时间。"""
    if extensions.redis_client is None:
        return {"count": 0, "retry_after": 0}
    try:
        count = extensions.redis_client.incr(key)
        if count == 1:
            extensions.redis_client.expire(key, window_seconds)
            ttl = window_seconds
        else:
            ttl = extensions.redis_client.ttl(key)
            if ttl is None or ttl < 0:
                extensions.redis_client.expire(key, window_seconds)
                ttl = window_seconds
        return {"count": count, "retry_after": ttl}
    except Exception:
        return {"count": 0, "retry_after": 0}


def rate_limit_reset(key: str):
    """在成功完成关键操作后清理对应失败计数。"""
    return cache_delete(key)


def rate_limit_consume(key: str, limit: int, window_seconds: int):
    """按固定时间窗口消费一次请求次数，并返回是否允许继续。"""
    if extensions.redis_client is None:
        return {"allowed": True, "count": 0, "retry_after": 0}
    try:
        count = extensions.redis_client.incr(key)
        if count == 1:
            extensions.redis_client.expire(key, window_seconds)
            ttl = window_seconds
        else:
            ttl = extensions.redis_client.ttl(key)
            if ttl is None or ttl < 0:
                extensions.redis_client.expire(key, window_seconds)
                ttl = window_seconds
        return {
            "allowed": count <= limit,
            "count": count,
            "retry_after": ttl if count > limit else 0,
        }
    except Exception:
        return {"allowed": True, "count": 0, "retry_after": 0}
