"""
The profiles page: the same order under two retailers' models, as the generator wrote it (profiles/exhibit.json).

Each retailer publishes its order profile as a model on the same components. What a model requires is read from
the assertions in its own schema; each retailer's first order of the year is written as its own UBL document, read
into both models and validated under each, and what each model refuses is named value by value. The page shows
the two models side by side, then the two orders under both.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from django.conf import settings

_docker_path = Path('/profiles')
_host_path = settings.BASE_DIR.parent.parent / 'profiles'
PROFILES_DIR = _docker_path if _docker_path.exists() else _host_path


def exhibit() -> Dict[str, Any]:
    p = PROFILES_DIR / 'exhibit.json'
    if not p.exists():
        return {'present': False}
    x = json.loads(p.read_text(encoding='utf-8'))
    x['present'] = True
    return x
