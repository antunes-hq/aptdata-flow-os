"""Google Calendar integration — OAuth2 + Calendar API wrapper."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any


def _get_credentials(store) -> Any | None:
    row = store.get("google_token", {})
    if not row or not row.get("refresh_token"):
        return None

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=row.get("token"),
        refresh_token=row["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(store, creds)

    return creds


def _save_credentials(store, creds) -> None:
    store.set(
        "google_token",
        {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        },
    )


def _build_service(store) -> Any:
    creds = _get_credentials(store)
    if not creds:
        return None
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=creds)


def get_auth_url(store) -> str:
    from google_auth_oauthlib.flow import Flow

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    if not redirect_uri:
        redirect_uri = (
            "https://mindflow.srv1723096.hstgr.cloud/api/calendar/auth/callback"
        )

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    flow.redirect_uri = redirect_uri
    auth_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    store.set("google_oauth_state", state)
    return auth_url


def handle_callback(store, code: str) -> bool:
    from google_auth_oauthlib.flow import Flow

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
    if not redirect_uri:
        redirect_uri = (
            "https://mindflow.srv1723096.hstgr.cloud/api/calendar/auth/callback"
        )

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    flow.redirect_uri = redirect_uri

    try:
        flow.fetch_token(code=code)
        _save_credentials(store, flow.credentials)
        return True
    except Exception:
        return False


def get_calendars(store) -> list[dict]:
    service = _build_service(store)
    if not service:
        return []
    result = service.calendarList().list().execute()
    return [
        {
            "id": c["id"],
            "summary": c.get("summary", ""),
            "primary": c.get("primary", False),
        }
        for c in result.get("items", [])
    ]


def list_events(
    store, calendar_id: str = "primary", date_str: str | None = None, days: int = 7
) -> list[dict]:
    service = _build_service(store)
    if not service:
        return []

    if date_str:
        tmin = datetime.fromisoformat(date_str)
    else:
        tmin = datetime.now()

    tmax = tmin + timedelta(days=days)

    result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=tmin.isoformat() + "Z",
            timeMax=tmax.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
            maxResults=20,
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        events.append(
            {
                "id": item["id"],
                "summary": item.get("summary", ""),
                "description": item.get("description", ""),
                "location": item.get("location", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "html_link": item.get("htmlLink", ""),
            }
        )

    return events


def create_event(store, calendar_id: str = "primary", **kwargs) -> dict | None:
    service = _build_service(store)
    if not service:
        return None

    event = {
        "summary": kwargs.get("summary", ""),
        "description": kwargs.get("description", ""),
        "start": {"dateTime": kwargs["start"], "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": kwargs["end"], "timeZone": "America/Sao_Paulo"},
    }
    if kwargs.get("location"):
        event["location"] = kwargs["location"]

    result = service.events().insert(calendarId=calendar_id, body=event).execute()
    return {
        "id": result["id"],
        "summary": result.get("summary", ""),
        "html_link": result.get("htmlLink", ""),
    }


def update_event(
    store, event_id: str, calendar_id: str = "primary", **kwargs
) -> dict | None:
    service = _build_service(store)
    if not service:
        return None

    event = {}
    for key in ("summary", "description", "location"):
        if key in kwargs and kwargs[key] is not None:
            event[key] = kwargs[key]
    if "start" in kwargs:
        event["start"] = {"dateTime": kwargs["start"], "timeZone": "America/Sao_Paulo"}
    if "end" in kwargs:
        event["end"] = {"dateTime": kwargs["end"], "timeZone": "America/Sao_Paulo"}

    result = (
        service.events()
        .update(calendarId=calendar_id, eventId=event_id, body=event)
        .execute()
    )
    return {"id": result["id"], "summary": result.get("summary", "")}


def delete_event(store, event_id: str, calendar_id: str = "primary") -> bool:
    service = _build_service(store)
    if not service:
        return False
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    return True
