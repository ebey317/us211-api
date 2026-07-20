"""Concrete assistant actions: email, print, text-to-speech, form-fill.

These are intentionally *thin* and *honest*. The us211-api service can build
the content and a ready-to-run instruction, but the actual side-effects
(sending email, printing, speaking) are executed by the agent/host environment
that has those capabilities. We never claim an email "sent" unless it did.

In the Hermes environment this module is imported by the host, which can wire
these to the real tools (email MCP, text_to_speech, etc.). When those tools are
not present, the functions return an honest status describing what *would*
happen, so the API stays usable and testable without a live mail server.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, Callable

from us211.agent import Action
from us211.models import Resource


@dataclass
class ActionResult:
    kind: str
    ok: bool
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


# Optional hooks the host can inject (e.g. Hermes email MCP, TTS tool).
_SEND_EMAIL_HOOK: Callable[..., Any] | None = None
_SPEAK_HOOK: Callable[[str], Any] | None = None
_PRINT_HOOK: Callable[[str], Any] | None = None


def register_hooks(
    send_email: Callable[..., Any] | None = None,
    speak: Callable[[str], Any] | None = None,
    print_doc: Callable[[str], Any] | None = None,
) -> None:
    """Let the host wire real capabilities (email/TTS/print) into the actions."""
    global _SEND_EMAIL_HOOK, _SPEAK_HOOK, _PRINT_HOOK
    _SEND_EMAIL_HOOK = send_email
    _SPEAK_HOOK = speak
    _PRINT_HOOK = print_doc


def _format_resources_markdown(resources: list[Resource], category: str, state: str) -> str:
    lines = [f"# 211 {category.title()} resources — {state}", ""]
    for r in resources:
        lines.append(f"## {r.organization.name}")
        if r.service and r.service.name:
            lines.append(f"**Service:** {r.service.name}")
        if r.phone:
            lines.append(f"**Phone:** {r.phone}")
        if r.address:
            lines.append(
                f"**Address:** {r.address.address_1}, {r.address.city}, "
                f"{r.address.state_province} {r.address.postal_code}"
            )
        if r.organization.url:
            lines.append(f"**Web:** {r.organization.url}")
        if r.service and r.service.description:
            lines.append(f"\n{r.service.description}")
        lines.append("")
    return "\n".join(lines)


def email_copy(
    resources: list[Resource], category: str, state: str, to: str
) -> ActionResult:
    """Email a copy of the results. Uses a real hook if registered, else a
    draft EmailMessage + honest 'not sent' status (no fabrication)."""
    body = _format_resources_markdown(resources, category, state)
    subject = f"211 {category.title()} help in {state}"
    if _SEND_EMAIL_HOOK is not None:
        try:
            _SEND_EMAIL_HOOK(to=to, subject=subject, body=body)
            return ActionResult("email", True, f"Emailed {len(resources)} resource(s) to {to}.", {"to": to})
        except Exception as exc:  # noqa: BLE001
            return ActionResult("email", False, f"Email failed: {exc}", {"to": to})
    # No hook: build the message but do NOT pretend it sent.
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["To"] = to
    msg.set_content(body)
    return ActionResult(
        "email",
        False,
        "Email not sent: no mail capability registered in this environment. "
        "Draft prepared; the assistant will send it where a mail tool is available.",
        {"draft_subject": subject, "to": to, "body_chars": len(body)},
    )


def speak(resource: Resource | list[Resource], category: str, state: str) -> ActionResult:
    """Read results aloud via the host TTS hook if present."""
    from us211.agent import read_aloud_script

    text = (
        read_aloud_script(resource, category, state)
        if isinstance(resource, list)
        else f"{resource.organization.name}. {resource.service.description or ''}"
    )
    if _SPEAK_HOOK is not None:
        try:
            _SPEAK_HOOK(text)
            return ActionResult("read_aloud", True, "Read aloud via text-to-speech.", {"chars": len(text)})
        except Exception as exc:  # noqa: BLE001
            return ActionResult("read_aloud", False, f"TTS failed: {exc}", {})
    return ActionResult(
        "read_aloud",
        False,
        "Text-to-speech not available in this environment. Script prepared for playback.",
        {"script": text},
    )


def print_list(resources: list[Resource], category: str, state: str) -> ActionResult:
    """Print-ready output. Uses host print hook if present."""
    doc = _format_resources_markdown(resources, category, state)
    if _PRINT_HOOK is not None:
        try:
            _PRINT_HOOK(doc)
            return ActionResult("print", True, "Sent to printer.", {"chars": len(doc)})
        except Exception as exc:  # noqa: BLE001
            return ActionResult("print", False, f"Print failed: {exc}", {})
    return ActionResult(
        "print",
        False,
        "Print not available in this environment. Print-ready document prepared.",
        {"doc_chars": len(doc)},
    )


def fill_form(resource: Resource, user_details: dict[str, str]) -> ActionResult:
    """Pre-fill an intake/application form from user details.

    We do NOT invent a working form endpoint. We produce a structured,
    ready-to-submit draft prefilled with the user's details and the resource's
    contact info, and (when a mail hook exists) email copies. Honest always.
    """
    draft = {
        "resource": resource.organization.name,
        "resource_phone": resource.phone,
        "resource_url": resource.organization.url,
        "applicant": user_details,
        "note": "Pre-filled intake draft. Review before submitting to the agency.",
    }
    detail = f"Prepared a pre-filled intake draft for {resource.organization.name}."
    if _SEND_EMAIL_HOOK is not None and user_details.get("email"):
        try:
            _SEND_EMAIL_HOOK(
                to=user_details["email"],
                subject=f"Pre-filled intake — {resource.organization.name}",
                body=str(draft),
            )
            detail += " Copies emailed automatically."
        except Exception as exc:  # noqa: BLE001
            detail += f" (auto-email failed: {exc})"
    return ActionResult("fill_form", True, detail, {"draft": draft})
