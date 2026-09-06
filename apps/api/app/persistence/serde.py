from __future__ import annotations

import base64
import json
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class PersistenceEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, bytes):
            return {"__bytes__": base64.b64encode(obj).decode("ascii")}
        return super().default(obj)


def persistence_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=PersistenceEncoder, ensure_ascii=False)


def persistence_loads(raw: str) -> Any:
    def hook(item: Any) -> Any:
        if isinstance(item, dict):
            if set(item.keys()) == {"__bytes__"}:
                return base64.b64decode(item["__bytes__"])
            return {k: hook(v) for k, v in item.items()}
        if isinstance(item, list):
            return [hook(v) for v in item]
        return item

    return hook(json.loads(raw))
