"""EI app ↔ BPEAI platform handshake constants (ei_handshake_v1)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, MutableMapping

HANDSHAKE_PROTOCOL_VERSION = "ei_handshake_v1"
OUTPUT_SCHEMA_VERSION = "equipment_selector_v1"

# Canonical options field; mixing_options is a read/write alias.
OPTIONS_FIELD = "evaluation_options"
OPTIONS_ALIAS = "mixing_options"


def normalize_options_fields(data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Ensure evaluation_options and mixing_options refer to the same list."""
    primary = data.get(OPTIONS_FIELD)
    alias = data.get(OPTIONS_ALIAS)
    if isinstance(primary, list) and primary:
        data[OPTIONS_FIELD] = primary
        data[OPTIONS_ALIAS] = primary
    elif isinstance(alias, list):
        data[OPTIONS_FIELD] = alias
        data[OPTIONS_ALIAS] = alias
    else:
        data[OPTIONS_FIELD] = primary if isinstance(primary, list) else []
        data[OPTIONS_ALIAS] = data[OPTIONS_FIELD]
    return data


def build_handshake_meta(
    *,
    run_id: str,
    app_id: str,
    history_run_id: str | None = None,
    release_version: str | None = None,
    pack_release_version: str | None = None,
    knowledge_pack_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "protocol_version": HANDSHAKE_PROTOCOL_VERSION,
        "run_id": run_id,
        "app_id": app_id,
    }
    if history_run_id:
        meta["history_run_id"] = history_run_id
    if release_version:
        meta["release_version"] = release_version
    if pack_release_version:
        meta["pack_release_version"] = pack_release_version
    if knowledge_pack_id:
        meta["knowledge_pack_id"] = knowledge_pack_id
    if extra:
        for k, v in extra.items():
            if v is not None and k not in meta:
                meta[k] = v
    return meta


def attach_handshake(result: MutableMapping[str, Any], meta: Mapping[str, Any]) -> MutableMapping[str, Any]:
    normalize_options_fields(result)
    result["_handshake"] = dict(meta)
    # Mirror common version fields for older clients
    result.setdefault("handshake_protocol", HANDSHAKE_PROTOCOL_VERSION)
    return result


def options_from_result(result: Mapping[str, Any]) -> List[Any]:
    primary = result.get(OPTIONS_FIELD)
    if isinstance(primary, list) and primary:
        return list(primary)
    alias = result.get(OPTIONS_ALIAS)
    if isinstance(alias, list):
        return list(alias)
    return []
