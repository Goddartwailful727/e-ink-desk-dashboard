from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = (BASE_DIR / "../data").resolve()
DDL_FILE = DATA_DIR / "ddl_data.json"
PLAN_FILE = DATA_DIR / "plan_data.json"
RECITE_FILE = DATA_DIR / "recite_data.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    _ensure_data_dir()
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, data: Any) -> None:
    _ensure_data_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def get_ddl_items() -> list[dict]:
    data = _read_json(DDL_FILE, [])
    if isinstance(data, dict):
        data = data.get("items", [])
    return data if isinstance(data, list) else []


def set_ddl_items(items) -> None:
    normalized = [dict(item) for item in items]
    _write_json(DDL_FILE, normalized)


def get_plan() -> dict:
    data = _read_json(PLAN_FILE, {})
    if not isinstance(data, dict):
        data = {}
    return {
        "date": data.get("date") or date.today().isoformat(),
        "items": data.get("items") if isinstance(data.get("items"), list) else [],
        "exams": data.get("exams") if isinstance(data.get("exams"), list) else [],
    }


def set_plan(items, exams) -> None:
    _write_json(
        PLAN_FILE,
        {
            "date": date.today().isoformat(),
            "items": [dict(item) for item in items],
            "exams": [dict(item) for item in exams],
        },
    )


def tick_plan_item(index) -> bool:
    plan = get_plan()
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return False
    if idx < 0 or idx >= len(plan["items"]):
        return False
    item = plan["items"][idx]
    item["done"] = not bool(item.get("done", False))
    _write_json(PLAN_FILE, plan)
    return True


def get_recite_text() -> str:
    data = _read_json(RECITE_FILE, {"text": ""})
    if isinstance(data, dict):
        return str(data.get("text", ""))
    return ""


def set_recite_text(text) -> None:
    _write_json(RECITE_FILE, {"text": str(text or "")})


def clear_recite_text() -> None:
    set_recite_text("")


def update_plan_item(index: int, updates: dict) -> bool:
    plan = get_plan()
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return False
    if idx < 0 or idx >= len(plan["items"]):
        return False
    plan["items"][idx].update(updates)
    _write_json(PLAN_FILE, plan)
    return True


def delete_plan_item(index: int) -> bool:
    plan = get_plan()
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return False
    if idx < 0 or idx >= len(plan["items"]):
        return False
    plan["items"].pop(idx)
    _write_json(PLAN_FILE, plan)
    return True


def add_plan_item(item: dict) -> bool:
    plan = get_plan()
    plan["items"].append(dict(item))
    _write_json(PLAN_FILE, plan)
    return True


def update_exam_item(index: int, updates: dict) -> bool:
    plan = get_plan()
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return False
    if idx < 0 or idx >= len(plan["exams"]):
        return False
    plan["exams"][idx].update(updates)
    _write_json(PLAN_FILE, plan)
    return True


def delete_exam_item(index: int) -> bool:
    plan = get_plan()
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return False
    if idx < 0 or idx >= len(plan["exams"]):
        return False
    plan["exams"].pop(idx)
    _write_json(PLAN_FILE, plan)
    return True


def add_exam_item(item: dict) -> bool:
    plan = get_plan()
    plan["exams"].append(dict(item))
    _write_json(PLAN_FILE, plan)
    return True
