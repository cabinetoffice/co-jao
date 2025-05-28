import httpx
from django.conf import settings


def get_async_client(session_key):
    """
    AsyncClient for accessing JAO backend, configured from Django.

    Session key must be provided to so that backend sessions match Django sessions.

    :param session_key: Session key to use for the client.
    :settings.JAO_BACKEND_ENABLE_HTTP2: Enable HTTP/2 for the client.
    """
    if not session_key:
        raise ValueError("Session key must not be empty.")

    return httpx.AsyncClient(
        http2=settings.JAO_BACKEND_ENABLE_HTTP2,
        base_url=settings.JAO_BACKEND_URL,
        headers={"X-Session-Id": session_key},
    )
