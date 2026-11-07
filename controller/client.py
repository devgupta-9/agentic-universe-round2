"""Finite read retries; callers must reconcile uncertain writes."""
import json
import time
import httpx


class APIError(Exception):
    def __init__(self, status, body):
        self.status, self.body = status, body
        super().__init__(f"HTTP {status}: {body}")


class UncertainWrite(Exception):
    """The remote side may have committed. Never blindly repeat the mutation."""


class API:
    def __init__(self, url, transport=None, retry_delay=.25):
        if not url.startswith(("http://", "https://")):
            raise ValueError("SIM_URL must use HTTP or HTTPS")
        self.http = httpx.Client(base_url=url.rstrip("/"), timeout=180, transport=transport, trust_env=False)
        self.retry_delay = retry_delay

    @staticmethod
    def decode(response):
        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text[:500]
            raise APIError(response.status_code, body)
        return response.json()

    def get(self, path, **params):
        for attempt in range(4):
            try:
                response = self.http.get(path, params=params)
                if response.status_code >= 500 and attempt < 3:
                    time.sleep(self.retry_delay * 2 ** attempt)
                    continue
                return self.decode(response)
            except httpx.TransportError:
                if attempt == 3:
                    raise
                time.sleep(self.retry_delay * 2 ** attempt)

    def write(self, method, path, body):
        try:
            response = self.http.request(method, path, json=body)
        except httpx.TransportError as error:
            raise UncertainWrite(str(error)) from error
        if response.status_code >= 500:
            raise UncertainWrite(f"HTTP {response.status_code} from {path}")
        try:
            return self.decode(response)
        except ValueError as error:
            raise UncertainWrite("Mutation response was not valid JSON") from error

    def events(self, chunk):
        with self.http.stream("GET", f"/events/chunks/{chunk}") as response:
            if response.status_code >= 400:
                response.read()
                self.decode(response)
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)

    def close(self):
        self.http.close()
