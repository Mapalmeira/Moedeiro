from fastapi import HTTPException, Request, status

from app.infrastructure.security.rate_limiter import RateLimitExceededError


def check_rate_limit(request: Request, rate: str, namespace: str) -> None:
    try:
        request.app.state.rate_limiter.check(rate, namespace, _client_ip(request))
    except RateLimitExceededError as error:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded", headers={"Retry-After": str(error.retry_after)}) from error


def _client_ip(request: Request) -> str:
    return "unknown" if request.client is None else request.client.host
