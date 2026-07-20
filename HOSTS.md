# HOSTS.md — wiring us211-api into any agent

`us211-api` does **not** send email, speak, or print on its own. Those are
*side-effects* that only an agent (with tools + an LLM loop) can perform. The
library exposes `us211.actions.register_hooks(...)` so **any** host agent can
plug in its own capabilities. This file shows three wirings. None are
required; without hooks the action functions return honest
`"draft prepared, not sent"` status.

The rule: **the agent supplies the tool, the library supplies the logic.**

---

## 1. Hermes (this project's home agent)

Hermes has an email MCP and a `text_to_speech` tool. Wire them by registering
hooks at startup (e.g. in a skill or session bootstrap):

```python
from us211.actions import register_hooks

def hermes_send_email(to: str, subject: str, body: str) -> None:
    # call the Hermes email MCP (or the scripts/email_mcp server) here
    ...

def hermes_speak(text: str) -> None:
    # call Hermes text_to_speech tool here
    ...

register_hooks(send_email=hermes_send_email, speak=hermes_speak)
```

After that, `actions.email_copy(...)` and `actions.speak(...)` actually send /
speak. (The exact Hermes call shape lives in the host's own tool docs, not here,
so this repo stays agent-agnostic.)

---

## 2. A CLI agent with SMTP (Kimi CLI / OpenCLAW / MiniMax / etc.)

Any agent that can run Python and reach an SMTP server can register a plain
function — no special SDK needed:

```python
import smtplib
from email.message import EmailMessage
from us211.actions import register_hooks

def smtp_send(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = "211-assistant@localhost"
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP("localhost") as s:
        s.send_message(msg)

register_hooks(send_email=smtp_send)  # speak/print left None -> honest "not available"
```

The same pattern works for a CLI agent that shells out to `say` / `espeak` for
TTS, or `lp` / `print` for printing — just pass those as the `speak=` / `print_doc=`
hooks.

---

## 3. Pseudocode for "any" agent

If your agent can import Python and expose callable tools, the contract is:

```
on startup:
    import us211.actions
    us211.actions.register_hooks(
        send_email = YOUR_agent_email_tool,
        speak      = YOUR_agent_tts_tool,
        print_doc  = YOUR_agent_print_tool,
    )

on user asks "what help can I get from <state>?":
    GET /ask?state=<state>&category=<category>
    show summary + resources
    offer the actions[] the API returned

on user picks an action:
    call the matching us211.actions.* function
    (it will use your registered hooks to actually do it)
```

That's the whole integration. The library never assumes Hermes, OpenAI,
Anthropic, or any specific vendor — only that *some* callable exists for each
side-effect.

---

## What each hook must satisfy

| Hook | Signature | Contract |
|------|-----------|----------|
| `send_email` | `(to: str, subject: str, body: str) -> None` | deliver the message; raise on failure |
| `speak` | `(text: str) -> None` | render `text` via TTS; raise on failure |
| `print_doc` | `(doc: str) -> None` | send `doc` to a printer; raise on failure |

If a hook is `None`, the corresponding action returns `ok=False` with an honest
message — never a false success.
