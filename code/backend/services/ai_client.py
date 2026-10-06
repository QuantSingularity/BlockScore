import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class AIModelClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        api_key: str = "",
        retries: int = 2,
        failure_threshold: int = 3,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or ""
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failures = 0
        self._open_until = 0.0
        self._lock = threading.Lock()
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            connect=retries,
            read=0,
            status=retries,
            backoff_factor=0.2,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET", "POST"}),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @classmethod
    def from_config(cls, config: Any) -> "AIModelClient":
        return cls(
            base_url=config.get("AI_MODEL_URL", "http://localhost:5001"),
            timeout=float(config.get("AI_MODEL_TIMEOUT", 5.0)),
            api_key=config.get("AI_MODEL_API_KEY", ""),
            retries=int(config.get("AI_MODEL_RETRIES", 2)),
            failure_threshold=int(config.get("AI_MODEL_FAILURE_THRESHOLD", 3)),
            cooldown_seconds=float(config.get("AI_MODEL_COOLDOWN_SECONDS", 30.0)),
        )

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _circuit_open(self) -> bool:
        with self._lock:
            return time.monotonic() < self._open_until

    def _record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._open_until = 0.0

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._open_until = time.monotonic() + self.cooldown_seconds
                self._failures = 0
                logger.warning(
                    "AI model service circuit opened for %.0fs", self.cooldown_seconds
                )

    def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not self.base_url or self._circuit_open():
            return None
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            logger.warning(
                "AI model service request %s %s failed: %s", method, path, exc
            )
            self._record_failure()
            return None
        if not isinstance(data, dict):
            logger.warning(
                "AI model service returned a non-object payload for %s", path
            )
            self._record_failure()
            return None
        self._record_success()
        return data

    def is_available(self) -> bool:
        if not self.base_url:
            return False
        try:
            response = self.session.get(
                f"{self.base_url}/health", timeout=min(self.timeout, 2.0)
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def model_info(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/model-info")

    def predict(self, credit_history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not credit_history:
            return None
        return self._request("POST", "/predict", {"creditHistory": credit_history})

    def batch_predict(
        self, items: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not items:
            return []
        data = self._request("POST", "/batch-predict", {"batch": items})
        if data is None:
            return None
        results = data.get("results")
        return results if isinstance(results, list) else None
