from typing import List, Optional, Dict
import json
import logging
import os
import ssl
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    import certifi
except ImportError:  # pragma: no cover
    certifi = None

from backend.schemas import Exercise

logger = logging.getLogger("workout_backend")

# SSL verification controls for fetching exercises JSON
# Set EXERCISES_SSL_VERIFY=false to bypass verification (not recommended for production)
EXERCISES_SSL_VERIFY = os.getenv("EXERCISES_SSL_VERIFY", "true").lower() not in {"0", "false", "no", "off"}
# Optionally provide a custom CA bundle path; if not set, we prefer certifi's bundle when available
EXERCISES_CA_BUNDLE = os.getenv("EXERCISES_CA_BUNDLE")


def _map_json_to_exercise(item: Dict) -> Optional[Exercise]:
    try:
        ex_id = int(item.get("exercise_id"))
        name = item.get("name") or f"Exercise {ex_id}"
        equipment_type = item.get("equipment_type")
        tm = item.get("target_muscle_groups") or {}
        primary = tm.get("primary") or []
        secondary = tm.get("secondary") or []
        muscle_group = ", ".join(primary) if primary else (", ".join(secondary) if secondary else "Unknown")
        utility = (item.get("utility") or "").strip().lower()
        if utility in {"cardio", "conditioning", "endurance", "aerobic"}:
            ex_type = "cardio"
        elif utility in {"mobility", "flexibility", "stability"}:
            ex_type = "mobility"
        else:
            ex_type = "strength"
        return Exercise(
            id=ex_id,
            name=name,
            muscle_group=muscle_group,
            equipment=equipment_type,
            type=ex_type,
        )
    except Exception:
        logger.debug("Failed to map exercise item to model: %s", item, exc_info=True)
        return None


def load_exercises_from_uri(uri: str, bearer_token: Optional[str] = None, timeout: float = 10.0) -> List[Exercise]:
    parsed = urlparse(uri)
    logger.debug(
        "Fetching exercises from URI=%s host=%s scheme=%s path=%s auth_present=%s",
        uri,
        parsed.netloc,
        parsed.scheme,
        parsed.path,
        bool(bearer_token),
    )
    try:
        headers = {"Accept": "application/json"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        req = Request(uri, headers=headers, method="GET")
        # Build SSL context for reliable certificate verification
        context = None
        try:
            if EXERCISES_SSL_VERIFY:
                if EXERCISES_CA_BUNDLE:
                    context = ssl.create_default_context(cafile=EXERCISES_CA_BUNDLE)
                elif certifi:
                    context = ssl.create_default_context(cafile=certifi.where())
                else:
                    context = ssl.create_default_context()
            else:
                context = ssl._create_unverified_context()
        except Exception as _ssl_err:
            logger.warning("Could not create SSL context, proceeding with default: %s", _ssl_err)
            context = None
        if context is not None:
            resp_ctx = urlopen(req, timeout=timeout, context=context)
        else:
            resp_ctx = urlopen(req, timeout=timeout)
        with resp_ctx as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            text = resp.read().decode(charset)
        data = json.loads(text)
        items = data.get("exercise_library", [])
        mapped: List[Exercise] = []
        for raw in items:
            ex = _map_json_to_exercise(raw)
            if ex:
                mapped.append(ex)
        logger.info("Fetched %d exercises from remote URI %s", len(mapped), parsed.netloc)
        return mapped
    except Exception as e:
        logger.error("Failed to load exercises from URI %s: %s", uri, e, exc_info=True)
        return []
