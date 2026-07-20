"""Minimal Open Referral HSDS data models (Pydantic v2).

This is a deliberately small subset of the full HSDS spec
(https://docs.openreferral.org) — enough to represent a single human-services
resource (a service, offered by an organization, at a location) in a shape that
is interoperable with HSDS consumers. Extend as adapters mature.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Organization(BaseModel):
    """An organization that provides one or more services."""

    id: str
    name: str
    description: str | None = None
    url: str | None = None
    email: str | None = None


class Service(BaseModel):
    """A service delivered by an organization."""

    id: str
    organization_id: str
    name: str
    description: str | None = None
    status: str = "active"


class Location(BaseModel):
    """A physical or virtual place where a service is delivered."""

    id: str
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PhysicalAddress(BaseModel):
    """A postal address for a location."""

    address_1: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str = "US"


class ServiceAtLocation(BaseModel):
    """Links a service to the location where it is offered."""

    id: str
    service_id: str
    location_id: str


class Resource(BaseModel):
    """A flattened envelope combining the HSDS entities for one result.

    This is the shape returned by the /resources endpoint. `category` is the
    normalized search category (food, housing, ...) and `source` names the 211
    the record came from (e.g. "Indiana 211").
    """

    category: str
    source: str
    organization: Organization
    service: Service
    location: Location | None = None
    address: PhysicalAddress | None = None
    phone: str | None = None
    detail_url: str | None = Field(default=None, description="Link to the source listing")
