# e2b Python SDK: Templates & Sandbox Lifecycle

A reference for using the [e2b Python SDK](https://pypi.org/project/e2b/) to build custom
sandbox templates and to start, pause/resume, and stop sandboxes.

- Examples written against **e2b `2.25.x`** (latest at time of writing: `2.25.1`, 2026-05-29).
- e2b runs AI-generated / untrusted code in secure, isolated cloud sandboxes.

> Versions matter here. The programmatic `Template` builder API (`Template().from_image(...)`,
> `Template.build(...)`) is part of the modern SDK / Build System 2.0. If you are on an older
> `0.x`/`1.x` SDK the template workflow is CLI + `e2b.toml`/`e2b.Dockerfile` based instead.

---

## 1. Installation & authentication

```bash
pip install e2b
```

Requires Python 3.10+.

Get an API key from the [e2b dashboard](https://e2b.dev/dashboard) and expose it to the SDK via
an environment variable:

```bash
export E2B_API_KEY="e2b_***"
```

The SDK reads `E2B_API_KEY` automatically. You can also pass it explicitly:

```python
from e2b import Sandbox

sbx = Sandbox.create(api_key="e2b_***")
```

For local development, loading a `.env` works well:

```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()  # picks up E2B_API_KEY from .env
```

---

## 2. Quick start

```python
from e2b import Sandbox

# Context manager auto-kills the sandbox on exit.
with Sandbox.create() as sandbox:
    result = sandbox.commands.run('echo "Hello from e2b!"')
    print(result.stdout)  # Hello from e2b!
```

> `e2b` (this package) gives you filesystem, command, and process control. To execute code
> snippets (e.g. run Python and capture rich outputs/charts), install the higher-level
> `e2b-code-interpreter` package, which adds `sandbox.run_code(...)`.

---

## 3. Creating templates

A **template** is a pre-configured sandbox image: base image, env vars, installed packages,
copied files, a working directory, and optionally a long-running **start command** that is
already running the moment a sandbox boots. Sandboxes are spawned *from* a template.

### 3.1 Scaffold with the CLI (easiest)

```bash
npm install -g @e2b/cli   # the e2b CLI ships via npm
e2b auth login
e2b template init         # interactive scaffold; read the generated README
```

### 3.2 Define a template programmatically (Python)

The modern SDK exposes a fluent `Template` builder:

```python
from e2b import Template, wait_for_timeout

template = (
    Template()
    .from_image("python:3.11")          # or .from_base_image() for the e2b default
    .set_envs({"HELLO": "Hello, World!"})
    .set_workdir("/app")
    .run_cmd("pip install numpy pandas") # runs at BUILD time, baked into the image
    .set_start_cmd(                       # runs at sandbox START, kept running
        "python -m http.server 8000",
        wait_for_timeout(5_000),          # readiness check: wait 5s before "ready"
    )
)
```

Common builder methods:

| Method | When it runs | Purpose |
| --- | --- | --- |
| `.from_image("python:3.11")` | build | Base from a Docker image |
| `.from_base_image()` | build | Base from e2b's default image |
| `.set_envs({...})` | build | Environment variables |
| `.set_workdir("/app")` | build | Default working directory |
| `.copy(src, dest)` | build | Copy local files into the image |
| `.run_cmd("...")` | build | Run a shell command during build (e.g. install deps) |
| `.set_start_cmd(cmd, ready)` | start | Long-running process started with each sandbox |
| `.set_ready_cmd(...)` / `wait_for_timeout(...)` | start | Readiness gating before the sandbox is usable |

### 3.3 Build the template

`Template.build()` uploads the definition and produces a reusable image addressed by its
`alias`. You also choose the default compute here.

```python
from e2b import Template

Template.build(
    template,
    alias="my-python-template",   # the name/tag you reference later
    cpu_count=2,                  # default 2
    memory_mb=2048,              # default 512; must be an even number
)
```

Tip: keep separate `build.dev.py` / `build.prod.py` scripts that build with different aliases
and resource sizes, or build from CI.

### 3.4 Use a built template

Reference it by alias when creating a sandbox:

```python
from e2b import Sandbox

sbx = Sandbox.create(template="my-python-template")
```

---

## 4. Sandbox lifecycle

### 4.1 Start / create

```python
from e2b import Sandbox

# Default template
sbx = Sandbox.create()

# From a custom template, with a 60s inactivity timeout
sbx = Sandbox.create(template="my-python-template", timeout=60)
```

`timeout` (seconds) is how long the sandbox stays alive before it is automatically shut down.
Extend it at runtime — the new value counts from *now*:

```python
sbx.set_timeout(30)  # alive for another 30 seconds from this call
```

Inspect a running sandbox:

```python
info = sbx.get_info()
# SandboxInfo: sandbox_id, template_id, name, metadata, started_at, end_at
print(sbx.sandbox_id)
```

> **Max runtime:** a single sandbox can run up to ~1 hour (Base tier) or ~24 hours (Pro tier).
> For longer-lived state, use pause/resume (below) to checkpoint and reset the runtime window.

### 4.2 Pause & resume

Pausing snapshots the **entire** sandbox — filesystem **and** memory (running processes,
loaded variables) — so resuming returns it to an identical state.

```python
from e2b import Sandbox

sbx = Sandbox.create()
sandbox_id = sbx.sandbox_id

sbx.pause()              # Running -> Paused (state is checkpointed)

# Later, from anywhere, reconnect & resume:
same_sbx = Sandbox.connect(sandbox_id, timeout=60)   # Paused -> Running
# If you still hold the object, sbx.connect() also resumes it.
```

**Auto-pause on timeout** — pause instead of kill when the timeout elapses:

```python
sandbox = Sandbox.create(
    timeout=10 * 60,                 # 10 minutes
    lifecycle={
        "on_timeout": "pause",      # pause (not kill) when idle timeout hits
        "auto_resume": False,
    },
)
```

### 4.3 Stop / kill

`kill()` terminates and **permanently deletes** the sandbox (paused sandboxes are deleted too):

```python
sbx.kill()                        # kill the one you hold

Sandbox.kill(sbx.sandbox_id)      # kill by ID (e.g. cleanup from elsewhere)
```

Prefer the context manager when the sandbox is short-lived — it kills on block exit even if an
exception is raised:

```python
with Sandbox.create(template="my-python-template") as sbx:
    sbx.commands.run("python main.py")
# sandbox is killed here automatically
```

---

## 5. State model at a glance

| Action | Method | Filesystem | Memory/processes | Billed/running |
| --- | --- | --- | --- | --- |
| Start | `Sandbox.create(...)` | fresh from template | start cmd running | yes |
| Pause | `sbx.pause()` | preserved | preserved | no (checkpointed) |
| Resume | `Sandbox.connect(id)` / `sbx.connect()` | restored | restored | yes |
| Kill | `sbx.kill()` / `Sandbox.kill(id)` | destroyed | destroyed | no (deleted) |

---

## 6. Gotchas

- **Set `E2B_API_KEY`** before importing/using the SDK, or pass `api_key=` explicitly.
- **Sync vs async:** the snippets above are the synchronous API. The SDK also ships an async
  client (`AsyncSandbox`) with the same method names — `await sbx.commands.run(...)` etc.
- **Template builder is version-gated.** `Template`/`Template.build` is the newer programmatic
  flow. Older SDKs use the CLI with `e2b.toml` + `e2b.Dockerfile`; check your installed version
  with `pip show e2b`.
- **`memory_mb` must be even**, defaults to 512; `cpu_count` defaults to 2.
- **`kill()` is permanent** — there is no undelete. Use `pause()` if you may need the state back.
- **`e2b` ≠ `e2b-code-interpreter`.** Install the latter if you need `run_code(...)` with rich
  output capture.

---

## References

- [e2b on PyPI](https://pypi.org/project/e2b/)
- [Sandbox docs](https://e2b.dev/docs/sandbox)
- [Sandbox persistence (pause/resume)](https://e2b.dev/docs/sandbox/persistence)
- [Sandbox templates](https://e2b.dev/docs/sandbox-template)
- [Build System 2.0 (blog)](https://e2b.dev/blog/introducing-build-system-2-0)
- [Custom CPU & RAM (blog)](https://e2b.dev/blog/customize-sandbox-compute)
