"""REST API reader plugin.

Provides :class:`APIReader` — a generic reader that fetches data from a
RESTful JSON endpoint using HTTP GET, with optional header injection
(e.g. for bearer tokens) and simple offset/page-based pagination.

Requires the optional ``httpx`` package.  A friendly
:class:`~aptdata.plugins.manager.PluginDependencyError` is raised
when it is not installed.
"""

from __future__ import annotations

from typing import Any

from aptdata.plugins.base import BaseReader
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.manager import PluginDependencyError


def _require_httpx() -> Any:
    """Import and return the ``httpx`` module, or raise a friendly error."""
    try:
        import httpx  # noqa: WPS433
    except ImportError:
        raise PluginDependencyError("APIReader", "httpx") from None
    return httpx


class APIReader(BaseReader):
    """Read JSON data from a REST API endpoint.

    Parameters
    ----------
    endpoint:
        The URL to send GET requests to.
    headers:
        Optional HTTP headers (e.g. ``{"Authorization": "Bearer xxx"}``).
    params:
        Optional query-string parameters merged into every request.
    pagination_key:
        When set, the reader fetches pages until the response JSON list is
        empty.  The value is the query-string parameter name that carries the
        page number (e.g. ``"page"``).  Pages start at ``1``.
    max_pages:
        Safety limit on the number of pages fetched (default ``100``).
    timeout:
        HTTP request timeout in seconds (default ``30``).
    records_path:
        Optional dot-separated path into the JSON response that contains
        the list of records (e.g. ``"data.items"``).  When ``None`` the
        response itself must be a JSON array.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        pagination_key: str | None = None,
        max_pages: int = 100,
        timeout: float = 30,
        records_path: str | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.headers = headers or {}
        self.params = params or {}
        self.pagination_key = pagination_key
        self.max_pages = max_pages
        self.timeout = timeout
        self.records_path = records_path

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _extract_records(body: Any, path: str | None) -> list[dict[str, Any]]:
        """Navigate *path* inside *body* and return the records list."""
        if path is None:
            if isinstance(body, list):
                return body
            raise ValueError(
                "Expected a JSON array from the API response. "
                "Set 'records_path' if records are nested."
            )
        current: Any = body
        for key in path.split("."):
            if isinstance(current, dict):
                current = current[key]
            else:
                raise ValueError(f"Cannot traverse key '{key}' in a non-dict value.")
        if not isinstance(current, list):
            raise ValueError(f"Expected a list at path '{path}', got {type(current).__name__}.")
        return current

    # -- BaseReader ---------------------------------------------------------

    def read(self, **kwargs: Any) -> InMemoryDataset:
        httpx = _require_httpx()

        all_records: list[dict[str, Any]] = []

        with httpx.Client(timeout=self.timeout) as client:
            if self.pagination_key is None:
                response = client.get(
                    self.endpoint, headers=self.headers, params=self.params,
                )
                response.raise_for_status()
                all_records = self._extract_records(response.json(), self.records_path)
            else:
                for page in range(1, self.max_pages + 1):
                    params = {**self.params, self.pagination_key: page}
                    response = client.get(
                        self.endpoint, headers=self.headers, params=params,
                    )
                    response.raise_for_status()
                    page_records = self._extract_records(response.json(), self.records_path)
                    if not page_records:
                        break
                    all_records.extend(page_records)

        ds = InMemoryDataset(uri=self.endpoint)
        ds.write(all_records)
        return ds


__all__ = ["APIReader"]
