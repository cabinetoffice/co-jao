import httpx
import pytest

from pytest_httpx import HTTPXMock

from jao_web.job_advert_optimiser.services.client import get_async_client


def test_client_session_key_cannot_be_empty():
    """Test that client creation requires a session key"""
    with pytest.raises(ValueError) as exc_info:
        get_async_client("")

    assert "Session key must not be empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_client_session_key_sets_session_id_header(httpx_mock: HTTPXMock, session_key, similar_applicants_url):
    """
    get_async_client requires a session key, and returns a client that should set the X-Session-Id header.

    Verify that the session id we pass through sets the client header X-Session-Id using the session key
    supplied earlier.
    """
    client = get_async_client(session_key)

    # Since the test is only checking headers, no body content is mocked here.
    httpx_mock.add_response(method="GET", url=similar_applicants_url, json={})

    await client.get("similar-applicants")
    assert isinstance(client, httpx.AsyncClient)

    request = httpx_mock.get_request()

    assert request.url == similar_applicants_url
    assert request.headers["X-Session-Id"] == session_key
