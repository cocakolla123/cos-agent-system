#!/usr/bin/env python3
"""Bring your own model: which model runs each job, and how to call it.

Every job the app runs (a chat reply, a draft, the first research crawl) has a
*tier*: ``light``, ``standard`` or ``deep``. The user picks a provider and a
model for each tier in Settings; the instructions are the same whichever model
runs them.

Providers:

- ``claude-code``: the user's Claude subscription through the ``claude`` CLI,
  which is also what holds the account connectors (Gmail, Slack...). A tier on
  it just adds ``--model`` to the CLI call. This is the default and needs no key.
- ``anthropic``: the Anthropic API with the user's key (official SDK, an
  optional install: ``pip install anthropic``).
- ``openai``, ``gemini``, ``openrouter``, ``ollama``: those APIs over plain
  HTTP (stdlib). OpenRouter and Ollama speak the OpenAI chat format.

Jobs that need account access (research, polls, learning, approvals) always
run through Claude Code, because that is where the connectors live; when their
tier names another provider they use Claude Code's default model and the
Settings page says so. Text-only jobs (chat, task chat, revise) run on any
provider.

Keys live in ``secrets.json`` next to the config (file mode 0600, ignored by
git) or in the provider's usual environment variable. They are sent only to
that provider.
"""

from __future__ import annotations

import json
import os
import stat
import urllib.error
import urllib.request

TIERS = ("light", "standard", "deep")

# job -> (tier, needs account tools)
JOBS = {
    "chat": ("light", False),
    "task_chat": ("light", False),
    "revise": ("standard", False),
    "draft": ("standard", True),
    "poll": ("standard", True),
    # the direct check: items are fetched by connections.py and sifted, so the
    # model only reads text and any provider can run it
    "poll_direct": ("standard", False),
    "accounts_probe": ("light", True),
    "research": ("deep", True),
    "learn": ("deep", True),
    # approving runs exactly the stored tool call; it stays on Claude Code
    # with its default model whatever the settings say
    "approve": (None, True),
}

PROVIDERS = {
    "claude-code": {"label": "Claude subscription (Claude Code)", "key_env": None,
                    "models": ["haiku", "sonnet", "opus", "fable"]},
    "anthropic": {"label": "Anthropic API", "key_env": "ANTHROPIC_API_KEY",
                  "models": ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5",
                             "claude-fable-5-1"]},
    "openai": {"label": "OpenAI API", "key_env": "OPENAI_API_KEY",
               "base": "https://api.openai.com/v1", "models": []},
    "gemini": {"label": "Google Gemini API", "key_env": "GEMINI_API_KEY",
               "base": "https://generativelanguage.googleapis.com/v1beta", "models": []},
    "openrouter": {"label": "OpenRouter (one key, many models)", "key_env": "OPENROUTER_API_KEY",
                   "base": "https://openrouter.ai/api/v1", "models": []},
    "ollama": {"label": "Ollama (local, free)", "key_env": None,
               "base": "http://localhost:11434/v1", "models": []},
}

# Effort per tier for Claude models that take it (Anthropic API).
TIER_EFFORT = {"light": "low", "standard": "medium", "deep": "high"}

# Presets offered in Settings. "subscription" is the zero-setup default the
# measured evals support: a Haiku crawl or Haiku polls lost tasks there
# (evals/results/longrun/REPORT.md), so only chat goes light.
PRESETS = {
    "subscription": {
        "light": {"provider": "claude-code", "model": "haiku"},
        "standard": {"provider": "claude-code", "model": "sonnet"},
        "deep": {"provider": "claude-code", "model": "opus"},
    },
    "anthropic-api": {
        "light": {"provider": "anthropic", "model": "claude-haiku-5-5"},
        "standard": {"provider": "anthropic", "model": "claude-sonnet-5-5"},
        "deep": {"provider": "anthropic", "model": "claude-opus-5-5"},
    },
}

CONFIG_FILE = "models.json"
SECRETS_FILE = "secrets.json"
TIMEOUT = 300


class ModelError(RuntimeError):
    pass


# ---------------------------------------------------------------- settings

def load(config_dir):
    """The tier settings: {"tiers": {tier: {"provider", "model"}}}. Missing
    tiers mean Claude Code with its own default model (the old behavior)."""
    try:
        with open(os.path.join(config_dir, CONFIG_FILE)) as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {}
    tiers = cfg.get("tiers") or {}
    out = {}
    for t in TIERS:
        v = tiers.get(t) or {}
        prov = v.get("provider") if v.get("provider") in PROVIDERS else "claude-code"
        eff = v.get("effort") if v.get("effort") in ("low", "medium", "high", "xhigh", "max") else ""
        out[t] = {"provider": prov, "model": str(v.get("model") or "").strip(), "effort": eff}
    return {"tiers": out}


def save(config_dir, tiers):
    """Validate and write the tier settings. Returns the saved dict."""
    clean = {}
    for t in TIERS:
        v = (tiers or {}).get(t) or {}
        prov = v.get("provider", "claude-code")
        if prov not in PROVIDERS:
            raise ModelError("unknown provider %r" % prov)
        model = str(v.get("model") or "").strip()
        if any(c.isspace() for c in model) or len(model) > 200:
            raise ModelError("model names have no spaces: %r" % model)
        eff = v.get("effort") or ""
        if eff and eff not in ("low", "medium", "high", "xhigh", "max"):
            raise ModelError("unknown effort %r" % eff)
        clean[t] = {"provider": prov, "model": model, "effort": eff}
    path = os.path.join(config_dir, CONFIG_FILE)
    try:
        with open(path) as f:
            cfg = json.load(f) or {}       # keep other settings (the budget)
    except (OSError, ValueError):
        cfg = {}
    cfg["tiers"] = clean
    with open(path, "w") as f:
        json.dump(cfg, f, indent=1)
    return {"tiers": clean}


def _secrets_path(config_dir):
    return os.path.join(config_dir, SECRETS_FILE)


def load_keys(config_dir):
    try:
        with open(_secrets_path(config_dir)) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if k in PROVIDERS and isinstance(v, str)}
    except (OSError, ValueError):
        return {}


def save_key(config_dir, provider, key):
    """Store one provider key (empty string removes it). Mode 0600."""
    if provider not in PROVIDERS or not PROVIDERS[provider]["key_env"]:
        raise ModelError("%s takes no key" % provider)
    keys = load_keys(config_dir)
    key = (key or "").strip()
    if key:
        keys[provider] = key
    else:
        keys.pop(provider, None)
    path = _secrets_path(config_dir)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(keys, f, indent=1)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def get_key(config_dir, provider):
    env = PROVIDERS.get(provider, {}).get("key_env")
    return load_keys(config_dir).get(provider) or (os.environ.get(env) if env else None)


def key_status(config_dir):
    """{provider: "saved" | "env" | "none" | "not needed"} — never the key."""
    saved = load_keys(config_dir)
    out = {}
    for p, meta in PROVIDERS.items():
        if not meta["key_env"]:
            out[p] = "not needed"
        elif p in saved:
            out[p] = "saved"
        elif os.environ.get(meta["key_env"]):
            out[p] = "env"
        else:
            out[p] = "none"
    return out


# ---------------------------------------------------------------- routing

def route(config_dir, job):
    """How to run ``job``: {"provider", "model", "tier", "note"}.

    A job that needs account tools on a tier set to another provider runs on
    Claude Code with its default model, and ``note`` says why."""
    tier, needs_tools = JOBS[job]
    if tier is None:
        return {"provider": "claude-code", "model": "", "tier": None, "note": ""}
    t = load(config_dir)["tiers"][tier]
    if needs_tools and t["provider"] != "claude-code":
        return {"provider": "claude-code", "model": "", "tier": tier,
                "note": "needs account access, so it runs on Claude Code"}
    return {"provider": t["provider"], "model": t["model"], "tier": tier, "note": ""}


EFFORTS = ("low", "medium", "high", "xhigh", "max")


def claude_args(config_dir, job):
    """Extra ``claude`` CLI arguments for a job routed to Claude Code: the
    tier's model and, when set, its effort (how hard the model thinks)."""
    r = route(config_dir, job)
    if r["provider"] != "claude-code" or r["tier"] is None:
        return []
    out = ["--model", r["model"]] if r["model"] else []
    eff = load(config_dir)["tiers"][r["tier"]].get("effort", "")
    if eff in EFFORTS:
        out += ["--effort", eff]
    return out


def uses_api(config_dir, job):
    """True when this job should go to an API provider instead of the CLI."""
    return route(config_dir, job)["provider"] != "claude-code"


# ---------------------------------------------------------------- calling

def _http(url, body=None, headers=None, timeout=TIMEOUT, method=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise ModelError("HTTP %d from %s: %s" % (e.code, url.split("?")[0], detail))
    except urllib.error.URLError as e:
        raise ModelError("could not reach %s: %s" % (url.split("?")[0], e.reason))


def _base(config_dir, provider):
    # a base URL override, for a self-hosted gateway or tests
    env = os.environ.get("COS_%s_BASE_URL" % provider.upper())
    return (env or PROVIDERS[provider]["base"]).rstrip("/")


def _openai_style(config_dir, provider, model, system, messages):
    key = get_key(config_dir, provider)
    if PROVIDERS[provider]["key_env"] and not key:
        raise ModelError("no %s key saved" % PROVIDERS[provider]["label"])
    msgs = ([{"role": "system", "content": system}] if system else []) + messages
    headers = {"Authorization": "Bearer " + key} if key else {}
    out = _http(_base(config_dir, provider) + "/chat/completions",
                {"model": model, "messages": msgs}, headers)
    try:
        return out["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        raise ModelError("unexpected reply from %s" % provider)


def _gemini(config_dir, model, system, messages):
    key = get_key(config_dir, "gemini")
    if not key:
        raise ModelError("no Gemini key saved")
    body = {"contents": [{"role": "model" if m["role"] == "assistant" else "user",
                          "parts": [{"text": m["content"]}]} for m in messages]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    out = _http("%s/models/%s:generateContent" % (_base(config_dir, "gemini"), model),
                body, {"x-goog-api-key": key})
    try:
        parts = out["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        raise ModelError("unexpected reply from Gemini")


def _anthropic_client(config_dir):
    try:
        import anthropic
    except ImportError:
        raise ModelError("the Anthropic API provider needs the SDK: pip install anthropic")
    key = get_key(config_dir, "anthropic")
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


# Models that take the server-side refusal fallback ("default" routing).
_FALLBACK_MODELS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")


def _anthropic(config_dir, model, system, messages, tier, client=None):
    client = client or _anthropic_client(config_dir)
    kwargs = {"model": model, "max_tokens": 16000, "messages": messages,
              "output_config": {"effort": TIER_EFFORT.get(tier or "standard", "medium")}}
    if system:
        kwargs["system"] = system
    if model in _FALLBACK_MODELS:
        # a policy decline is retried on a suitable model inside the same call
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"],
                                           fallbacks="default", **kwargs)
    else:
        resp = client.messages.create(**kwargs)
    if getattr(resp, "stop_reason", None) == "refusal":
        raise ModelError("the model declined this request")
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


def complete(config_dir, job, prompt, system=None, history=None, _client=None,
             _route=None):
    """Run a text-only job on its routed API provider. ``history`` is a list
    of {"role": "user"|"assistant", "content": str} before ``prompt``.
    Raises ModelError; never called for Claude Code routes."""
    r = _route or route(config_dir, job)
    if r["provider"] == "claude-code":
        raise ModelError("job %s runs on Claude Code" % job)
    if not r["model"]:
        raise ModelError("pick a model for the %s tier in Settings" % r["tier"])
    messages = [m for m in (history or []) if m.get("content")] + [
        {"role": "user", "content": prompt}]
    p = r["provider"]
    if p == "anthropic":
        return _anthropic(config_dir, r["model"], system, messages, r["tier"], _client)
    if p == "gemini":
        return _gemini(config_dir, r["model"], system, messages)
    return _openai_style(config_dir, p, r["model"], system, messages)


def list_models(config_dir, provider, _client=None):
    """Model ids the provider says the key can use (asks the provider; no
    guessing). Claude Code returns its aliases."""
    if provider not in PROVIDERS:
        raise ModelError("unknown provider %r" % provider)
    if provider == "claude-code":
        return list(PROVIDERS[provider]["models"])
    if provider == "anthropic":
        client = _client or _anthropic_client(config_dir)
        return sorted(m.id for m in client.models.list())
    if provider == "gemini":
        key = get_key(config_dir, "gemini")
        if not key:
            raise ModelError("no Gemini key saved")
        out = _http(_base(config_dir, "gemini") + "/models", headers={"x-goog-api-key": key})
        return sorted(m["name"].split("/", 1)[-1] for m in out.get("models", [])
                      if "generateContent" in (m.get("supportedGenerationMethods") or []))
    key = get_key(config_dir, provider)
    if PROVIDERS[provider]["key_env"] and not key:
        raise ModelError("no %s key saved" % PROVIDERS[provider]["label"])
    out = _http(_base(config_dir, provider) + "/models",
                headers={"Authorization": "Bearer " + key} if key else {})
    return sorted(m["id"] for m in out.get("data", []) if m.get("id"))


def test(config_dir, provider, model, _client=None):
    """Send one tiny request to a provider and model. Returns the reply text;
    raises ModelError."""
    if provider == "claude-code":
        raise ModelError("Claude Code is tested by running a job, not here")
    return complete(config_dir, "chat", "Reply with the single word: ready",
                    _client=_client, _route={"provider": provider, "model": model,
                                             "tier": "light", "note": ""})


if __name__ == "__main__":
    # poll-tick.sh: print one CLI argument per line for a job routed to Claude Code
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "claude-args" and sys.argv[2] in JOBS:
        print("\n".join(claude_args(sys.argv[3], sys.argv[2])))
