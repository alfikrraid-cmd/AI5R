from __future__ import annotations


class LoadBalancer:
    def __init__(self):
        self.counter = 0

    def next_worker(self, workers: list[str]) -> str:
        if not workers:
            raise ValueError("No workers available")

        worker = workers[self.counter % len(workers)]
        self.counter += 1

        return worker
