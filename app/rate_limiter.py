from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def rate_limit_key(request: Request) -> str:
    # Si viene la cabecera, la usamos como clave para el rate limit
    header_key = request.headers.get("X-RateLimit-Key")
    if header_key:
        return header_key

    # Si no hay cabecera, se cae al comportamiento normal (IP)
    return get_remote_address(request)



limiter = Limiter(key_func=rate_limit_key)
