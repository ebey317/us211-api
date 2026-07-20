"""Abstract adapter contract. Each 211 platform implements one of these."""
from __future__ import annotations

from abc import ABC, abstractmethod

from us211.models import Resource


class BaseAdapter(ABC):
    """Contract for a platform adapter.

    An adapter knows how to talk to ONE 211 platform (VisionLink, iCarol,
    findhelp, ...) and return results normalized into HSDS `Resource` objects.
    """

    #: Normalized category -> platform-specific taxonomy term. Subclasses fill in.
    CATEGORY_MAP: dict[str, str] = {}

    def __init__(self, base_url: str | None, source_name: str, timeout: float = 15.0):
        self.base_url = base_url
        self.source_name = source_name
        self.timeout = timeout

    @abstractmethod
    async def search(
        self,
        category: str,
        postal_code: str | None = None,
        state: str | None = None,
    ) -> list[Resource]:
        """Search the platform and return normalized resources.

        Implementations MUST NOT fabricate data. If the upstream returns
        nothing usable, return an empty list rather than inventing results.
        """
        raise NotImplementedError
