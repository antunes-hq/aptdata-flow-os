"""Contract tests for F1.3 — Browser Grant HTTP Adapter.

Each test maps to one acceptance criterion from the workpacket.
All tests are offline/deterministic — no network, no FastAPI, no
Starlette, no credentials, no Nuvem, no aptdata/mcp/server.py.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from aptdata.auth import (
    BrowserGrantHttpAdapter,
    BrowserGrantHttpRequest,
    BrowserSessionGrantStore,
)
from aptdata.auth.browser_grant_http import (
    _GRANT_PATH_RE,
    _MUTABLE_SCOPES,
    _has_mutable_scopes,
    _security_headers,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path: Path) -> BrowserSessionGrantStore:
    return BrowserSessionGrantStore(db_path=str(tmp_path / "http_grants.db"))


@pytest.fixture()
def adapter(store: BrowserSessionGrantStore) -> BrowserGrantHttpAdapter:
    return BrowserGrantHttpAdapter(
        store=store,
        expected_workspace="ws-main",
        expected_project="proj-alpha",
        expected_run="run-42",
        secure=True,
    )


@pytest.fixture()
def adapter_insecure(
    store: BrowserSessionGrantStore,
) -> BrowserGrantHttpAdapter:
    return BrowserGrantHttpAdapter(
        store=store,
        expected_workspace="ws-main",
        expected_project="proj-alpha",
        expected_run="run-42",
        secure=False,
    )


_VALID_SCOPES = ("run:read", "flow:read", "artifact:read")


@pytest.fixture()
def valid_grant(store: BrowserSessionGrantStore) -> str:
    return store.issue(
        workspace_id="ws-main",
        project_id="proj-alpha",
        run_id="run-42",
        scopes=_VALID_SCOPES,
    )


# ---------------------------------------------------------------------------
# Helper: build a request
# ---------------------------------------------------------------------------


def _get(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="GET", path=path)


def _post(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="POST", path=path)


def _put(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="PUT", path=path)


def _delete_request(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="DELETE", path=path)


def _patch(path: str) -> BrowserGrantHttpRequest:
    return BrowserGrantHttpRequest(method="PATCH", path=path)


# ===========================================================================
# Acceptance criteria (1–15)
# ===========================================================================


class TestAc1ValidRequestReturns303:
    """Criterion 1: request válida retorna 303."""

    def test_valid_redeem_returns_303(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 303, (
            f"Expected 303, got {response.status_code}"
        )


class TestAc2ResponseHasHttpOnlySetCookie:
    """Criterion 2: resposta tem Set-Cookie HttpOnly."""

    def test_set_cookie_httponly_present(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "HttpOnly" in set_cookie, (
            f"Set-Cookie missing HttpOnly: {set_cookie}"
        )
        assert "browser_session_id=" in set_cookie


class TestAc3SecurePolicyEnforced:
    """Criterion 3: resposta tem Secure conforme policy."""

    def test_secure_true_when_policy_secure(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Secure" in set_cookie, (
            f"Set-Cookie missing Secure: {set_cookie}"
        )

    def test_secure_false_when_policy_insecure(
        self,
        adapter_insecure: BrowserGrantHttpAdapter,
        valid_grant: str,
        store: BrowserSessionGrantStore,
    ):
        # Need a new grant because the first fixture consumed it
        grant2 = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=_VALID_SCOPES,
        )
        path = f"/access/{grant2}"
        response = adapter_insecure.redeem_access_request(_get(path))
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "Secure" not in set_cookie, (
            f"Set-Cookie should not have Secure: {set_cookie}"
        )


class TestAc4SecurityHeadersPresent:
    """Criterion 4: resposta tem no-store/no-referrer/nosniff."""

    def test_security_headers(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        expected = _security_headers()
        for header, value in expected.items():
            actual = response.headers.get(header, "")
            assert actual == value, (
                f"Expected {header}: {value!r}, got {actual!r}"
            )


class TestAc5LocationNoGrant:
    """Criterion 5: Location não contém o grant."""

    def test_location_no_grant(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        location = response.headers.get("Location", "")
        assert valid_grant not in location, (
            f"Location contains grant: {location}"
        )
        assert location == "/universe/ws-main/proj-alpha/run-42"

    def test_location_no_grant_hash(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        ghash = hashlib.sha256(valid_grant.encode()).hexdigest()
        response = adapter.redeem_access_request(_get(path))
        location = response.headers.get("Location", "")
        assert ghash not in location, (
            "Location contains grant hash"
        )


import hashlib  # noqa: E402 — must be after the test that uses it


class TestAc6SecondRequestFails401:
    """Criterion 6: segundo request com mesmo grant falha 401."""

    def test_second_redeem_returns_401(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        path = f"/access/{valid_grant}"
        # First redeem — succeeds
        first = adapter.redeem_access_request(_get(path))
        assert first.status_code == 303

        # Second redeem with same grant — fails
        second = adapter.redeem_access_request(_get(path))
        assert second.status_code == 401, (
            f"Expected 401, got {second.status_code}: "
            f"{second.body.decode()}"
        )


class TestAc7MissingMalformedGrantReturns400:
    """Criterion 7: grant ausente/malformado retorna 400."""

    def test_missing_grant_returns_400(self, adapter: BrowserGrantHttpAdapter):
        response = adapter.redeem_access_request(_get("/access/"))
        assert response.status_code == 400

    def test_no_grant_segment_returns_400(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        response = adapter.redeem_access_request(_get("/access"))
        assert response.status_code == 400

    def test_short_grant_returns_400(self, adapter: BrowserGrantHttpAdapter):
        response = adapter.redeem_access_request(
            _get("/access/abc123")
        )
        assert response.status_code == 400

    def test_hex_grant_too_short_returns_400(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        path = "/access/" + "a" * 63  # 63 hex chars, not 64
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 400

    def test_non_hex_grant_returns_400(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        path = "/access/" + "z" * 64  # non-hex chars
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 400


class TestAc8ExpiredRevokedInvalidReturns401:
    """Criterion 8: grant expirado/revogado/inválido retorna 401 sem segredo."""

    def test_invalid_grant_returns_401(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        path = "/access/" + "0" * 64
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 401

    def test_revoked_grant_returns_401(
        self,
        adapter: BrowserGrantHttpAdapter,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=_VALID_SCOPES,
        )
        store.revoke(raw)
        path = f"/access/{raw}"
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 401

    def test_error_body_no_raw_grant(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        path = "/access/" + "a" * 64
        response = adapter.redeem_access_request(_get(path))
        body = response.body.decode()
        assert "0" * 64 not in body
        assert "a" * 64 not in body

    def test_error_body_no_stack_trace(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        path = "/access/" + "b" * 64
        response = adapter.redeem_access_request(_get(path))
        body = response.body.decode()
        assert "Traceback" not in body
        assert "File" not in body

    def test_error_body_no_grant_hash(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        fake_grant = "c" * 64
        path = f"/access/{fake_grant}"
        response = adapter.redeem_access_request(_get(path))
        body = response.body.decode()
        for line in body.splitlines():
            assert "sha256" not in line.lower(), (
                f"Body contains hash reference: {line}"
            )


class TestAc9ContextMismatchReturns403:
    """Criterion 9: contexto incorreto retorna 403."""

    def test_wrong_workspace_still_403(
        self,
        store: BrowserSessionGrantStore,
        valid_grant: str,
    ):
        # Adapter expects ws-main but the store has the grant for ws-main
        # This is a special case — a legitimate workspace match wouldn't
        # get 403.  Let's test with a grant issued for a different workspace.
        raw2 = store.issue(
            workspace_id="ws-other",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=_VALID_SCOPES,
        )
        adapter2 = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",  # mismatch
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        path = f"/access/{raw2}"
        response = adapter2.redeem_access_request(_get(path))
        assert response.status_code == 403, (
            f"Expected 403 for workspace mismatch, got {response.status_code}: "
            f"{response.body.decode()}"
        )

    def test_wrong_run_returns_403(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-99",
            scopes=_VALID_SCOPES,
        )
        adapter_run = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",  # mismatch with run-99
        )
        path = f"/access/{raw}"
        response = adapter_run.redeem_access_request(_get(path))
        assert response.status_code == 403, (
            f"Expected 403 for run mismatch, got {response.status_code}"
        )

    def test_wrong_project_returns_403(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-other",
            run_id="run-42",
            scopes=_VALID_SCOPES,
        )
        adapter_project = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter_project.redeem_access_request(_get(f"/access/{raw}"))
        assert response.status_code == 403


class TestAc10NonGetReturns405:
    """Criterion 10: método diferente de GET retorna 405."""

    @pytest.mark.parametrize(
        "method, make_req",
        [
            ("POST", _post),
            ("PUT", _put),
            ("DELETE", _delete_request),
            ("PATCH", _patch),
            ("HEAD", lambda p: BrowserGrantHttpRequest(method="HEAD", path=p)),
            ("OPTIONS", lambda p: BrowserGrantHttpRequest(method="OPTIONS", path=p)),
        ],
        ids=["POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )
    def test_non_get_returns_405(
        self,
        adapter: BrowserGrantHttpAdapter,
        method: str,
        make_req: object,
    ):
        response = adapter.redeem_access_request(
            make_req("/access/" + "d" * 64)  # type: ignore[operator]
        )
        assert response.status_code == 405, (
            f"Expected 405 for {method}, got {response.status_code}"
        )
        assert b"Method Not Allowed" in response.body


class TestAc11MutableScopeRejected:
    """Criterion 11: scope mutável é rejeitado."""

    @pytest.mark.parametrize(
        "mutable_scope",
        sorted(_MUTABLE_SCOPES),
        ids=sorted(_MUTABLE_SCOPES),
    )
    def test_mutable_scope_rejected(
        self,
        store: BrowserSessionGrantStore,
        mutable_scope: str,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=(mutable_scope,),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        path = f"/access/{raw}"
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 403, (
            f"Expected 403 for mutable scope {mutable_scope!r}, "
            f"got {response.status_code}: {response.body.decode()}"
        )

    def test_read_only_scopes_accepted(
        self,
        store: BrowserSessionGrantStore,
        valid_grant: str,
    ):
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        path = f"/access/{valid_grant}"
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 303, (
            f"Expected 303 for read-only scopes, got {response.status_code}"
        )

    def test_mutable_scope_detected_no_store(
        self,
    ):
        """Unit-test the _has_mutable_scopes helper directly."""
        assert _has_mutable_scopes(("deploy",))
        assert _has_mutable_scopes(("run:read", "deploy"))
        assert not _has_mutable_scopes(("run:read",))
        assert not _has_mutable_scopes(())


class TestAc12ErrorBodyNoRawGrantHashStacktrace:
    """Criterion 12: body de erro não contém raw grant/hash/stack trace."""

    def test_all_error_bodies_safe(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        """Verify multiple error paths produce safe bodies."""
        test_cases = [
            ("/access/", 400),
            ("/access/" + "0" * 64, 401),  # valid hex, not in store
            ("/access/" + "f" * 63, 400),
            ("/not-access/grant", 400),
        ]
        for path, expected_status in test_cases:
            response = adapter.redeem_access_request(_get(path))
            assert response.status_code == expected_status, (
                f"Path {path}: expected {expected_status}, "
                f"got {response.status_code}"
            )
            body = response.body.decode()
            # Check for suspicious leaks
            assert "<raw-grant>" not in body
            assert "<hash>" not in body
            assert "Traceback" not in body
            assert "File" not in body
            # Body should be short — under 200 chars
            assert len(body) < 200, (
                f"Error body too long ({len(body)} chars): {body}"
            )

    def test_405_error_body_safe(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        response = adapter.redeem_access_request(
            BrowserGrantHttpRequest(method="DELETE", path="/access/anything")
        )
        assert response.status_code == 405
        body = response.body.decode()
        assert len(body) < 200
        assert "Traceback" not in body
        assert "<grant>" not in body.lower()

    def test_403_error_body_safe(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=_VALID_SCOPES + ("deploy",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        path = f"/access/{raw}"
        response = adapter.redeem_access_request(_get(path))
        assert response.status_code == 403
        body = response.body.decode()
        assert len(body) < 200
        assert "deploy" not in body
        assert raw not in body


class TestAc13UrlNotLogged:
    """Criterion 13: URL completa não é logada."""

    def test_full_url_not_in_logs(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
        caplog: pytest.LogCaptureFixture,
    ):
        caplog.set_level(logging.DEBUG)
        path = f"/access/{valid_grant}"
        adapter.redeem_access_request(_get(path))
        combined_log = caplog.text
        # The full grant value should not appear in logs
        assert valid_grant not in combined_log, (
            "Raw grant leaked in log output"
        )
        # The path /access/<grant> should not appear either
        assert path not in combined_log, (
            "Full URL path leaked in log output"
        )

    def test_error_url_not_in_logs(
        self,
        adapter: BrowserGrantHttpAdapter,
        caplog: pytest.LogCaptureFixture,
    ):
        caplog.set_level(logging.DEBUG)
        fake = "h" * 64
        path = f"/access/{fake}"
        adapter.redeem_access_request(_get(path))
        combined_log = caplog.text
        assert fake not in combined_log, (
            "Fake grant leaked in log output"
        )

    def test_unexpected_error_message_not_in_logs(
        self,
        adapter: BrowserGrantHttpAdapter,
        caplog: pytest.LogCaptureFixture,
        valid_grant: str,
    ):
        class SensitiveStore:
            def redeem(self, *args: object, **kwargs: object):
                raise RuntimeError("sensitive-internal-value")

        adapter._store = SensitiveStore()  # type: ignore[assignment]
        with caplog.at_level(logging.DEBUG):
            response = adapter.redeem_access_request(_get(f"/access/{valid_grant}"))
        assert response.status_code == 401
        assert "sensitive-internal-value" not in caplog.text


class TestAc14NoNetworkNoFrameworkNoCredentials:
    """Criterion 14: testes não usam rede, FastAPI, Starlette ou credenciais.

    This is a structural test — it verifies that no import from these
    packages appears in the tests or the adapter module.
    """

    # Packages that should NOT be importable by the adapter or tests
    _FORBIDDEN = frozenset({
        "fastapi",
        "starlette",
        "flask",
        "httpx",
        "aiohttp",
        "requests",
    })

    def test_no_forbidden_imports_in_adapter(self):
        import ast

        adapter_path = (
            Path(__file__).resolve().parent.parent
            / "aptdata" / "auth" / "browser_grant_http.py"
        )
        source = adapter_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in self._FORBIDDEN, (
                        f"Forbidden import {alias.name} in adapter"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top not in self._FORBIDDEN, (
                        f"Forbidden import {node.module} in adapter"
                    )

    def test_no_forbidden_imports_in_test(self):
        import ast

        test_path = Path(__file__).resolve()
        source = test_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top not in self._FORBIDDEN, (
                        f"Forbidden import {alias.name} in test"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    assert top not in self._FORBIDDEN, (
                        f"Forbidden import {node.module} in test"
                    )


class TestAc15NoMpcServerNoNuvem:
    """Criterion 15: aptdata/mcp/server.py e Nuvem não são tocados."""

    def test_no_mcp_server_import(self):
        """Verify the adapter never imports from aptdata.mcp.server."""
        import ast

        adapter_path = (
            Path(__file__).resolve().parent.parent
            / "aptdata" / "auth" / "browser_grant_http.py"
        )
        source = adapter_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                module = (
                    node.module
                    if isinstance(node, ast.ImportFrom)
                    else (node.names[0].name if node.names else "")
                )
                if module and "mcp" in module.lower():
                    pytest.fail(f"Adapter imports from mcp: {module}")
                if module and "nuvem" in module.lower():
                    pytest.fail(f"Adapter imports from nuvem: {module}")

    def test_nuvem_not_imported_in_test(self):
        import ast

        test_path = Path(__file__).resolve()
        source = test_path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                module = (
                    node.module
                    if isinstance(node, ast.ImportFrom)
                    else (node.names[0].name if node.names else "")
                )
                if module and "mcp" in module.lower():
                    pytest.fail(f"Test imports from mcp: {module}")
                if module and "nuvem" in module.lower():
                    pytest.fail(f"Test imports from nuvem: {module}")


# ===========================================================================
# Unit-level coverage for helpers
# ===========================================================================


class TestHelpers:
    def test_grant_path_re_valid(self):
        g = "a" * 64
        m = _GRANT_PATH_RE.match(f"/access/{g}")
        assert m is not None
        assert m.group(1) == g

    def test_grant_path_re_invalid(self):
        assert _GRANT_PATH_RE.match("/access/") is None
        assert _GRANT_PATH_RE.match("/access/nothex") is None
        assert _GRANT_PATH_RE.match("/access/" + "a" * 63) is None
        assert _GRANT_PATH_RE.match("/access/" + "z" * 64) is None
        assert _GRANT_PATH_RE.match("/other/aaaa") is None

    def test_security_headers_structure(self):
        headers = _security_headers()
        assert headers["Cache-Control"] == "no-store"
        assert headers["Pragma"] == "no-cache"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert len(headers) == 4

    def test_mutable_scopes_defined(self):
        assert "approval:respond" in _MUTABLE_SCOPES
        assert "deploy" in _MUTABLE_SCOPES
        assert "delete" in _MUTABLE_SCOPES
        assert "admin" in _MUTABLE_SCOPES
        assert "write" in _MUTABLE_SCOPES

    def test_redeem_with_security_headers_on_200_level(
        self,
        adapter: BrowserGrantHttpAdapter,
        valid_grant: str,
    ):
        """Error responses should also carry security headers."""
        response = adapter.redeem_access_request(_get(f"/access/{valid_grant}"))
        assert response.status_code == 303
        h = response.headers
        assert h.get("Cache-Control") == "no-store"
        assert h.get("Pragma") == "no-cache"

    def test_redeem_error_also_has_security_headers(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        response = adapter.redeem_access_request(
            _get("/access/" + "0" * 64)
        )
        assert response.status_code == 401
        h = response.headers
        assert h.get("Cache-Control") == "no-store"
        assert h.get("Referrer-Policy") == "no-referrer"

    def test_405_has_security_headers(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        response = adapter.redeem_access_request(
            BrowserGrantHttpRequest(method="POST", path="/access/" + "j" * 64)
        )
        assert response.status_code == 405
        h = response.headers
        assert h.get("Cache-Control") == "no-store"
        assert h.get("Referrer-Policy") == "no-referrer"
        assert h.get("X-Content-Type-Options") == "nosniff"

    def test_400_has_security_headers(
        self,
        adapter: BrowserGrantHttpAdapter,
    ):
        response = adapter.redeem_access_request(_get("/access/short"))
        assert response.status_code == 400
        h = response.headers
        assert h.get("Cache-Control") == "no-store"

    def test_mutable_scope_rejection_has_security_headers(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("admin",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(_get(f"/access/{raw}"))
        assert response.status_code == 403
        h = response.headers
        assert h.get("Cache-Control") == "no-store"

    def test_mutable_scope_rejection_has_no_body_leak(
        self,
        store: BrowserSessionGrantStore,
    ):
        raw = store.issue(
            workspace_id="ws-main",
            project_id="proj-alpha",
            run_id="run-42",
            scopes=("deploy",),
        )
        adapter = BrowserGrantHttpAdapter(
            store=store,
            expected_workspace="ws-main",
            expected_project="proj-alpha",
            expected_run="run-42",
        )
        response = adapter.redeem_access_request(_get(f"/access/{raw}"))
        body = response.body.decode()
        assert "deploy" not in body
