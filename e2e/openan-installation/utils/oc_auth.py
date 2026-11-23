from __future__ import annotations

import json
import time

from utils.shell import EVIDENCE_DIR, curl_request, save_evidence

LOGIN_PATH = "/api/orchestrate/rest/v1/orchestrate/auth/login"
CHANGE_PASSWORD_PATH = "/api/orchestrate/rest/v1/orchestrate/auth/change-password"
# The frontend nginx only proxies the OC API under /api/orchestrate/; the bare
# /api/v1/auth/token path is 404 there.
TOKEN_PATH = "/api/orchestrate/api/v1/auth/token"
JSON_HEADERS = ["Content-Type: application/json"]


def _post(base: str, path: str, payload: dict, cookie_jar=None, evidence_stem: str | None = None):
    body, status = curl_request(
        "POST",
        f"{base}{path}",
        data=json.dumps(payload),
        headers=JSON_HEADERS,
        cookie_jar=cookie_jar,
    )
    if evidence_stem:
        save_evidence(f"{evidence_stem}-{path.replace('/', '_').strip('_')}", f"{status}\n{body}")
    return body, status


def get_admin_token(base: str, initial_password: str, evidence_stem: str | None = None):
    """Obtain an OC admin Bearer token, handling the first-boot forced password change.

    Flow per the OC auth contract: the first token call with the initial password
    returns 403 Password change required (no token issued). The web login then
    issues a session cookie, /auth/change-password clears the flag, and the token
    call succeeds with the new password. On re-runs against kept data the password
    may already be the derived changed one; both are tried.
    """
    changed_password = initial_password + "1aA!"

    body, status = _post(base, TOKEN_PATH, {"username": "admin", "password": initial_password}, evidence_stem=evidence_stem)
    if status == "200" and "access_token" in body:
        return body, status, initial_password

    if status == "403" and "Password change required" in body:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        cookie_jar = EVIDENCE_DIR / f"oc-session-{time.strftime('%Y%m%d-%H%M%S')}.cookies"
        login_body, login_status = _post(
            base,
            LOGIN_PATH,
            {"username": "admin", "password": initial_password},
            cookie_jar=cookie_jar,
            evidence_stem=evidence_stem,
        )
        if login_status != "200":
            return login_body, login_status, initial_password
        change_body, change_status = _post(
            base,
            CHANGE_PASSWORD_PATH,
            {"old_password": initial_password, "new_password": changed_password},
            cookie_jar=cookie_jar,
            evidence_stem=evidence_stem,
        )
        if change_status != "200":
            return change_body, change_status, initial_password
        body, status = _post(
            base,
            TOKEN_PATH,
            {"username": "admin", "password": changed_password},
            evidence_stem=evidence_stem,
        )
        return body, status, changed_password

    body, status = _post(
        base,
        TOKEN_PATH,
        {"username": "admin", "password": changed_password},
        evidence_stem=evidence_stem,
    )
    if status == "200" and "access_token" in body:
        return body, status, changed_password
    return body, status, initial_password
