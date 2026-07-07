from BUSINESS_VERTICALS.UMKM_OS.RUNTIME import AI5RUMKMOSRuntime
from BUSINESS_VERTICALS.SCHOOL_OS.RUNTIME import SchoolRuntime
from BUSINESS_VERTICALS.AUDITOR_OS.RUNTIME import AuditorRuntime


class VerticalRegistry:
    def __init__(self):
        self._verticals = {
            "UMKM_OS": AI5RUMKMOSRuntime,
            "SCHOOL_OS": SchoolRuntime,
            "AUDITOR_OS": AuditorRuntime,
        }

    def names(self):
        return list(self._verticals.keys())

    def get(self, name):
        return self._verticals[name]

    def create(self, name, root_path="."):
        return self._verticals[name](root_path=root_path)
