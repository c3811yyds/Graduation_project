import ipaddress

from flask import request


def _normalize_ip(ip_text: str) -> str:
    """统一清洗 IP 字符串，避免前后空格影响判断。"""
    return (ip_text or "").strip()


def _is_valid_ip(ip_text: str) -> bool:
    """校验字符串是否为合法 IPv4 或 IPv6 地址。"""
    try:
        ipaddress.ip_address(_normalize_ip(ip_text))
        return True
    except ValueError:
        return False


def _is_trusted_proxy(ip_text: str) -> bool:
    """仅在请求来自本机或内网代理时才信任转发头。"""
    try:
        address = ipaddress.ip_address(_normalize_ip(ip_text))
    except ValueError:
        return False
    return address.is_loopback or address.is_private


def request_client_ip() -> str:
    """优先提取反向代理转发过来的真实客户端 IP。"""
    remote_ip = _normalize_ip(request.remote_addr) or "unknown"
    if _is_trusted_proxy(remote_ip):
        forwarded_for = _normalize_ip((request.headers.get("X-Forwarded-For") or "").split(",")[0])
        if _is_valid_ip(forwarded_for):
            return forwarded_for

        real_ip = _normalize_ip(request.headers.get("X-Real-IP"))
        if _is_valid_ip(real_ip):
            return real_ip

    return remote_ip
