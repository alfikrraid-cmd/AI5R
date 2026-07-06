from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import inspect
import pkgutil
import sys


@dataclass
class DependencyGraph:
    nodes: dict[str, list[str]] = field(default_factory=dict)

    def add_edge(self, module: str, dependency: str):
        self.nodes.setdefault(module, [])

        if dependency not in self.nodes[module]:
            self.nodes[module].append(dependency)

    def snapshot(self):
        return dict(self.nodes)


class DependencyGraphAnalyzer:
    def __init__(self, root_package: str = "AI5R_SDK"):
        self.root_package = root_package
        self.graph = DependencyGraph()

    def scan_modules(self):
        import AI5R_SDK

        return [
            m.name
            for m in pkgutil.walk_packages(
                AI5R_SDK.__path__,
                AI5R_SDK.__name__ + "."
            )
        ]

    def analyze(self):
        modules = self.scan_modules()

        for module in modules:
            try:
                mod = importlib.import_module(module)
            except Exception:
                continue

            self.graph.nodes.setdefault(module, [])

            for name, obj in inspect.getmembers(mod):
                if inspect.ismodule(obj):
                    self.graph.add_edge(module, obj.__name__)
                elif hasattr(obj, "__module__"):
                    dep = getattr(obj, "__module__", None)
                    if dep and dep != module:
                        self.graph.add_edge(module, dep)

        return self.graph
