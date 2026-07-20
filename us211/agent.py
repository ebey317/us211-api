"""Agent capabilities: what the 211 assistant can DO with results.

This is the layer that makes us211-api more than a search box. When a person
asks "what help can I get from Indiana?" we return a slew of info; when they
say "I need those food pantries" we return a list AND proactively offer
actions: read it aloud, print it, email a copy, summarize, pinpoint the exact
document/form, or fill out an application.

Each capability is a small, honest function. None of them fabricate outcomes:
- summarize / read_aloud / pinpoint: pure text transforms over real data
- print / email / fill_form: return a structured, ready-to-run *instruction*
  (the agent/host executes it) — we never pretend an email "sent" unless it did
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from us211.models import Resource


@dataclass
class Action:
    """A recommended or executed action the assistant offers the user."""

    kind: str  # read_aloud | print | email | summarize | pinpoint | fill_form
    label: str
    detail: str
    payload: dict[str, Any] = field(default_factory=dict)


# Human-readable catalog surfaced in /ask and the README.
CAPABILITIES: list[dict] = [
    {
        "kind": "summarize",
        "label": "Summarize",
        "detail": "Turn a long list of results into a short, plain-language summary.",
    },
    {
        "kind": "read_aloud",
        "label": "Read aloud (text-to-speech)",
        "detail": "Read the results or a single resource out loud for hands-free / low-vision access.",
    },
    {
        "kind": "print",
        "label": "Print",
        "detail": "Generate a print-ready version of the list or one resource.",
    },
    {
        "kind": "email",
        "label": "Email me a copy",
        "detail": "Email the list (or one resource) to an address the user provides. Auto-attaches copies of any forms.",
    },
    {
        "kind": "pinpoint",
        "label": "Pinpoint the exact document",
        "detail": "Jump straight to the specific resource / form / page instead of digging through a whole site.",
    },
    {
        "kind": "fill_form",
        "label": "Fill out the form for me",
        "detail": "Pre-fill an application or intake form from the user's details, then email copies automatically.",
    },
]


def summarize(resources: list[Resource], category: str, state: str) -> str:
    """Plain-language summary of a result set."""
    if not resources:
        return f"No {category} resources were found for {state} right now."
    lines = [f"Found {len(resources)} {category} resource(s) in {state}:"]
    for r in resources[:5]:
        name = r.organization.name
        loc = f" in {r.address.city}, {r.address.state_province}" if r.address else ""
        phone = f" — call {r.phone}" if r.phone else ""
        lines.append(f"• {name}{loc}{phone}")
    if len(resources) > 5:
        lines.append(f"…and {len(resources) - 5} more.")
    return "\n".join(lines)


def read_aloud_script(resources: list[Resource], category: str, state: str) -> str:
    """A spoken script for text-to-speech playback."""
    if not resources:
        return f"I'm sorry, I couldn't find any {category} help in {state} right now."
    parts = [f"Here are {len(resources)} {category} options in {state}."]
    for i, r in enumerate(resources[:5], 1):
        name = r.organization.name
        if r.address:
            parts.append(
                f"{i}. {name}, located at {r.address.address_1}, {r.address.city}, {r.address.state_province} {r.address.postal_code}."
            )
        else:
            parts.append(f"{i}. {name}.")
        if r.phone:
            parts.append(f"You can call them at {r.phone}.")
    return " ".join(parts)


def pinpoint(resource: Resource) -> Action:
    """Build a 'jump to the exact document/page' action for one resource."""
    target = resource.organization.url or (
        resource.address and f"{resource.address.city}, {resource.address.state_province}"
    )
    return Action(
        kind="pinpoint",
        label="Open this resource",
        detail=f"Go straight to {resource.organization.name}"
        + (f" — {resource.organization.url}" if resource.organization.url else "."),
        payload={"url": resource.organization.url, "name": resource.organization.name},
    )


def recommend_actions(resources: list[Resource]) -> list[Action]:
    """Proactively offer the actions a good assistant would suggest."""
    actions: list[Action] = []
    if resources:
        actions.append(
            Action(
                kind="summarize",
                label="Summarize these results",
                detail="Get a short plain-language summary instead of the raw list.",
            )
        )
        actions.append(
            Action(
                kind="read_aloud",
                label="Read results aloud",
                detail="Hands-free / low-vision playback via text-to-speech.",
            )
        )
        actions.append(
            Action(
                kind="print",
                label="Print this list",
                detail="Generate a print-ready version of all results.",
            )
        )
        actions.append(
            Action(
                kind="email",
                label="Email me a copy",
                detail="Send the list (and any forms) to your email automatically.",
            )
        )
        # If we have a URL, offer to jump straight there.
        if any(r.organization.url for r in resources):
            actions.append(
                Action(
                    kind="pinpoint",
                    label="Pinpoint the exact page",
                    detail="Skip the search — open the specific resource page directly.",
                )
            )
        # If any resource looks like it has an intake/application step.
        if any(r.service and r.service.description for r in resources):
            actions.append(
                Action(
                    kind="fill_form",
                    label="Fill out an application for me",
                    detail="Pre-fill an intake form from your details, then email copies automatically.",
                )
            )
    return actions
