from __future__ import annotations

import importlib


class LazyLoader:
    def __init__(self):
        self._cache = {}

    def load(self, module_name: str):
        if module_name in self._cache:
            return self._cache[module_name]

        module = importlib.import_module(module_name)
        self._cache[module_name] = module

        return module
