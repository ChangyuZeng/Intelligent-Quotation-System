"""端口选择与"是否已有本系统在跑"的探测。"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request

PREFERRED_PORT = 8000
PORT_RANGE = range(8000, 8011)

# 只探本机回环地址：显式禁用代理，避免公司电脑配置了 HTTP_PROXY 时
# 请求被转发到代理服务器，导致"服务明明起来了却判定为未就绪"。
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def health(port: int, timeout: float = 0.6) -> dict | None:
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        with _OPENER.open(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def running_instance() -> int | None:
    """已有本系统在运行时返回其端口（用来避免重复启动）。"""
    for port in PORT_RANGE:
        payload = health(port)
        if payload and payload.get("service") == "quote-api":
            return port
    return None


def pick() -> int | None:
    for port in PORT_RANGE:
        if is_free(port):
            return port
    return None
