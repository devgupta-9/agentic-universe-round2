import httpx
import pytest
from controller.client import API, UncertainWrite, APIError


def test_get_retries_but_a_mutation_is_never_blindly_retried():
    attempts = []
    def handler(request):
        attempts.append(request.method)
        raise httpx.ReadTimeout("response lost", request=request)
    api = API("http://test", transport=httpx.MockTransport(handler), retry_delay=0)
    with pytest.raises(httpx.ReadTimeout):
        api.get("/sim/state")
    assert len(attempts) == 4
    attempts.clear()
    with pytest.raises(UncertainWrite):
        api.write("POST", "/approvals", {"proposal_id": "stable"})
    assert attempts == ["POST"]


def test_business_error_is_not_retried():
    attempts = []
    def handler(request):
        attempts.append(1)
        return httpx.Response(409, json={"error": "stale_base_version", "detail": "changed"})
    api = API("http://test", transport=httpx.MockTransport(handler), retry_delay=0)
    with pytest.raises(APIError) as error:
        api.write("POST", "/approvals", {})
    assert error.value.status == 409 and len(attempts) == 1
