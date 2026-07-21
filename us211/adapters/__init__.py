"""Adapter registry / factory."""
from __future__ import annotations

from us211.adapters.base import BaseAdapter
from us211.adapters.findhelp import FindhelpAdapter
from us211.adapters.icarol import iCarolAdapter
from us211.adapters.visionlink import VisionLinkAdapter
from us211.registry import PlatformType, Source

__all__ = ["BaseAdapter", "VisionLinkAdapter", "FindhelpAdapter", "iCarolAdapter", "get_adapter"]


def get_adapter(source: Source) -> BaseAdapter | None:
    """Return an adapter instance for a registry Source, or None if unwired."""
    if source.platform is PlatformType.VISIONLINK:
        return VisionLinkAdapter(base_url=source.base_url, source_name=source.name)
    if source.platform is PlatformType.FINDHELP:
        return FindhelpAdapter(base_url=source.base_url, source_name=source.name)
    if source.platform is PlatformType.ICAROL:
        return iCarolAdapter(base_url=source.base_url, source_name=source.name)
    return None