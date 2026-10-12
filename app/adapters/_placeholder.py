"""Base for adapters that are planned but not built yet (AWS, Azure).

They are registered so config, docs and tests already know about them, and they fail fast
at startup with a clear message instead of failing halfway through a request.
"""


class PlannedProvider:
    cloud: str = "?"
    service: str = "?"

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            f"The {self.cloud} adapter ({self.service}) is a placeholder. "
            "See docs/multicloud.md for the interface to implement."
        )
