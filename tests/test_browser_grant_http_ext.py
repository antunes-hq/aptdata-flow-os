"""Extension tests: dynamic project/run resolution and base_url for F1.4.

These tests verify the new features added to BrowserGrantHttpAdapter for
the Control Plane browser link workpacket.

Tests are offline/deterministic — no network, no FastAPI, no credentials.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aptdata.auth import (
    BrowserGrantHttpAdapter,
    BrowserGrantHttpRequest,
    BrowserSessionGrantStore,
)

# ---------------------------------------------------------------------------
# Helpers (mirrored from test_browser_grant_http.py for independence)
# ---------------------------------------------------------------------------


def _get(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="GET", path=path)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> BrowserSessionGrantStore:
    return BrowserSessionGrantStore(db_path=str(tmp_path / "ext_grants.db"))


# ---------------------------------------------------------------------------
# Dynamic project/run tests
# ---------------------------------------------------------------------------


class TestDynamicProjectRun:
    """expected_project/expected_run=None resolves from grant."""

    def test_dynamic_both_resolved_from_grant(
        self,
        store: BrowserSessionGrantStore,
    ):
        """When expected_project/run are None, use the grant's stored values."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-dynamic",
            run_id="run-dynamic-99",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project=None,
            expected_run=None,
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        assert response.status_code == 303
        location = response.headers.get("Location", "")
        assert "proj-dynamic" in location, (
            f"Expected project from grant, got: {location}"
        )
        assert "run-dynamic-99" in location, (
            f"Expected run from grant, got: {location}"
        )

    def test_dynamic_project_static_run(
        self,
        store: BrowserSessionGrantStore,
    ):
        """When run is static but project is None, run is validated."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-foo",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project=None,
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        assert response.status_code == 303
        location = response.headers.get("Location", "")
        assert "proj-foo" in location
        assert "run-42" in location

    def test_dynamic_project_run_mismatch_rejected(
        self,
        store: BrowserSessionGrantStore,
    ):
        """Static run mismatch is still rejected even with dynamic project."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-foo",
            run_id="run-99",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project=None,
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        assert response.status_code == 403

    def test_static_project_mismatch_rejected(
        self,
        store: BrowserSessionGrantStore,
    ):
        """Static project mismatch is rejected (backward compat)."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-other",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# base_url tests
# ---------------------------------------------------------------------------


class TestBaseUrl:
    """base_url makes Location absolute."""

    def test_base_url_makes_absolute_location(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
            base_url="https://flow.example.com",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        location = response.headers.get("Location", "")
        assert location.startswith("https://flow.example.com/")
        assert "/universe/ws-main/proj-alpha/run-42" in location

    def test_trailing_slash_handled(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
            base_url="https://flow.example.com/",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        location = response.headers.get("Location", "")
        assert location == "https://flow.example.com/universe/ws-main/proj-alpha/run-42"

    def test_no_base_url_relative(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        location = response.headers.get("Location", "")
        assert location == "/universe/ws-main/proj-alpha/run-42"

    def test_base_url_with_dynamic(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-dynamic",
            run_id="run-dynamic-99",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project=None,
            expected_run=None,
            base_url="https://flow.example.com",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        location = response.headers.get("Location", "")
        expected = "https://flow.example.com/universe/ws-main/proj-dynamic/run-dynamic-99"
        assert location == expected, f"Expected {expected}, got {location}"


# ---------------------------------------------------------------------------
# cookie_domain tests
# ---------------------------------------------------------------------------


class TestCookieDomain:
    """cookie_domain adds Domain attribute to Set-Cookie."""

    def test_cookie_domain_present_in_set_cookie(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
            cookie_domain=".example.com",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Domain=.example.com" in set_cookie, (
            f"Expected Domain in Set-Cookie, got: {set_cookie}"
        )

    def test_cookie_domain_default_absent(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Domain=" not in set_cookie, (
            f"Expected no Domain in Set-Cookie, got: {set_cookie}"
        )

    def test_cookie_domain_with_base_url(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
            base_url="https://flow.example.com",
            cookie_domain=".example.com",
        )
        response = adapter.redeem_access_request(
            _get(f"/access/{raw}")
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Domain=.example.com" in set_cookie, (
            f"Expected Domain in Set-Cookie, got: {set_cookie}"
        )
        location = response.headers.get("Location", "")
        assert location.startswith("https://flow.example.com/")
        assert location == "https://flow.example.com/universe/ws-main/proj-alpha/run-42"


# ---------------------------------------------------------------------------
# redeem_grant tests — anti-preview fragment flow
# ---------------------------------------------------------------------------


class TestRedeemGrant:
    """Tests for the public redeem_grant method (POST/fragment flow)."""

    def test_redeem_grant_valid_returns_303(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Valid raw grant directly -> 303 with cookie and location."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
            base_url="https://flow.example.com",
        )
        response = adapter.redeem_grant(raw)
        assert response.status_code == 303
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "HttpOnly" in set_cookie
        location = response.headers.get("Location", "")
        assert location.startswith("https://flow.example.com/")

    def test_redeem_grant_malformed_returns_400(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Malformed raw grant (short, non-hex, empty, uppercase) -> 400."""
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        assert adapter.redeem_grant("abc123").status_code == 400
        assert adapter.redeem_grant("z" + "0" * 63).status_code == 400
        assert adapter.redeem_grant("").status_code == 400
        assert adapter.redeem_grant("A" + "0" * 63).status_code == 400

    def test_redeem_grant_invalid_returns_401(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Non-existent grant -> 401."""
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        assert adapter.redeem_grant("0" * 64).status_code == 401

    def test_redeem_grant_second_use_returns_401(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Second redeem_grant with same grant -> 401 (one-shot)."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        assert adapter.redeem_grant(raw).status_code == 303
        assert adapter.redeem_grant(raw).status_code == 401

    def test_redeem_grant_workspace_mismatch_returns_403(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Wrong workspace -> 403."""
        raw = store.issue(
            workspace_id="ws-other",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        assert adapter.redeem_grant(raw).status_code == 403

    def test_redeem_grant_no_grant_in_body_or_log(
        self,
        store: BrowserSessionGrantStore,
    ) -> None:
        """Response body and headers never contain the raw grant."""
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("run:read",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_grant(raw)
        body_str = response.body.decode() if response.body else ""
        for header_value in response.headers.values():
            assert raw not in header_value, (
                f"Raw grant leaked in header: {header_value}"
            )
        assert raw not in body_str, f"Raw grant leaked in body: {body_str}"
