from __future__ import annotations

import copy
import uuid
from typing import Any


_VERSION_STORE: dict[str, list[dict[str, Any]]] = {}


def _service_map(architecture: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    architecture = architecture or {}
    result: dict[str, dict[str, Any]] = {}
    for service in architecture.get("services", []) or []:
        name = str(service.get("name", "")).strip()
        if name:
            result[name.lower()] = service
    return result


def _connection_set(architecture: dict[str, Any] | None) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for connection in (architecture or {}).get("connections", []) or []:
        if isinstance(connection, (list, tuple)) and len(connection) >= 2:
            result.add((str(connection[0]), str(connection[1])))
        elif isinstance(connection, dict):
            source = connection.get("source") or connection.get("from")
            target = connection.get("target") or connection.get("to")
            if source and target:
                result.add((str(source), str(target)))
    return result


def create_architecture_version(
    session_id: str,
    architecture: dict[str, Any],
    reason: str,
    label: str | None = None,
) -> dict[str, Any]:
    versions = _VERSION_STORE.setdefault(session_id, [])
    version_number = len(versions) + 1
    snapshot = {
        "version_id": f"arch-{uuid.uuid4().hex[:10]}",
        "version": version_number,
        "label": label or f"V{version_number}",
        "reason": reason,
        "architecture": copy.deepcopy(architecture),
    }
    versions.append(snapshot)
    return snapshot


def get_architecture_versions(session_id: str) -> list[dict[str, Any]]:
    return copy.deepcopy(_VERSION_STORE.get(session_id, []))


def compare_architectures(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    before_services = _service_map(before)
    after_services = _service_map(after)
    before_connections = _connection_set(before)
    after_connections = _connection_set(after)

    added_keys = sorted(set(after_services) - set(before_services))
    removed_keys = sorted(set(before_services) - set(after_services))
    common_keys = sorted(set(before_services) & set(after_services))

    changed = []
    for key in common_keys:
        old = before_services[key]
        new = after_services[key]
        if old.get("type") != new.get("type"):
            changed.append({
                "name": new.get("name") or old.get("name"),
                "before_type": old.get("type"),
                "after_type": new.get("type"),
            })

    return {
        "added_components": [after_services[key] for key in added_keys],
        "removed_components": [before_services[key] for key in removed_keys],
        "changed_components": changed,
        "added_connections": [list(item) for item in sorted(after_connections - before_connections)],
        "removed_connections": [list(item) for item in sorted(before_connections - after_connections)],
        "summary": {
            "components_added": len(added_keys),
            "components_removed": len(removed_keys),
            "components_changed": len(changed),
            "connections_added": len(after_connections - before_connections),
            "connections_removed": len(before_connections - after_connections),
        },
    }


def compare_versions(session_id: str, before_version: int, after_version: int) -> dict[str, Any]:
    versions = _VERSION_STORE.get(session_id, [])
    before = next((item for item in versions if item["version"] == before_version), None)
    after = next((item for item in versions if item["version"] == after_version), None)
    if not before or not after:
        raise ValueError("Requested architecture version was not found.")
    return {
        "before": {k: before[k] for k in ("version_id", "version", "label", "reason")},
        "after": {k: after[k] for k in ("version_id", "version", "label", "reason")},
        "diff": compare_architectures(before["architecture"], after["architecture"]),
    }
