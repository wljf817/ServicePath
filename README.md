# ServicePath

ServicePath is an AI-assisted website connectivity diagnostic tool. Give it a
public HTTP(S) address and it collects bounded network evidence, identifies the
earliest observed failure layer, and saves a report with practical next steps.
Checks run on the ServicePath host, not in the browser.

Results are classified as reachable, degraded, or unreachable. Each report
includes evidence, failure stage, confidence, causes, and next steps. Invalid
configuration, tool failures, and unsupported conclusions stop the run with an
error, and no report is saved.

Tool calls and their returned evidence stream to the browser while the Agent
is running; the completed report is saved only after final validation.

## Checks

| Stage | Evidence |
| --- | --- |
| Client | IPv4/IPv6 route availability and system proxy detection |
| DNS | A/AAAA records, resolution failures, and public-address validation |
| Route | A short, optional `traceroute` or `tracert` |
| TCP | Connection results for the target's effective port |
| TLS | Trust, hostname, protocol, cipher, and certificate expiry |
| HTTP | Redirects, status, title, server header, and basic CDN/WAF signals |

The Agent can only use server-owned, read-only tools. The target is normalized
and locked before execution, while tool calls, Agent turns, response samples,
redirects, and execution times are bounded. Evidence summaries displayed in a
report are generated from tool results rather than model-authored claims.

## Local setup

Requirements:

- Python 3.10 or newer
- An OpenAI-compatible model API with tool calling and JSON output
- `traceroute` on macOS/Linux or `tracert` on Windows for route evidence
- Node.js only when changing the frontend

Create an environment and install the application:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
```

Configure at least the model key and name in `.env`:

```dotenv
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5.6
```

For DeepSeek:

```dotenv
OPENAI_API_KEY=your_deepseek_key
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_MODE=chat_completions
```

Start the local server:

```bash
python app.py
```

Open `http://127.0.0.1:5050`. Reports are stored in
`instance/servicepath.db`. Set `SERVICEPATH_DEBUG=1` only when Flask debug mode
is intentionally needed.

## Docker deployment

Docker Engine or Docker Desktop with the Compose plugin is required. Create
`.env` from `.env.example`, then generate two different secrets by running this
command twice:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store the results in `.env`:

```dotenv
SETTINGS_PASSWORD=first_random_value
SERVICEPATH_API_TOKEN=second_random_value
```

Set the model variables there as well, or configure OpenAI from Settings
after startup. Build and start the service:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f servicepath
```

The container runs Gunicorn as an unprivileged user with a read-only root
filesystem, dropped Linux capabilities, and a `/healthz` readiness check. The
safe default publishes port 5050 only on `127.0.0.1`.

Change the host interface with `SERVICEPATH_BIND_ADDRESS` and the published port
with `SERVICEPATH_PORT`. Keep the loopback default unless a trusted reverse
proxy or another deliberate network boundary handles controlled external access.

On the first start of a new volume, selected container variables are written to
the private `/data/.env`. That persistent copy becomes authoritative, so
changes made in Settings survive container replacement and are not overwritten
by an older host `.env`. Reports are stored in `/data/servicepath.db` in the
same `servicepath-data` volume.

Upgrade without deleting data:

```bash
docker compose down
docker compose build --pull
docker compose up -d
```

`docker compose down -v` permanently deletes saved settings and reports. The
current SQLite and runtime-settings design supports one container only; do not
scale it horizontally. A public reverse proxy should allow at least five
minutes for a diagnosis request. A Client Test inside Docker observes the
container's network namespace, not the host's exact network path.

## Execution modes

- **Server Test** runs on the current process when its role is `server`; a
  `client` sends it to the endpoint fixed by `REMOTE_SERVICE_URL` at deployment.
- **Client Test** runs directly on the current `client` device.

The default role is `server`, which permits only Server Test because a hosted
page cannot inspect a visitor's raw network path. Install ServicePath on the
device being investigated and select `client` when client evidence is required.
The client and server must use the same `SERVICEPATH_API_TOKEN`. The server URL
is deployment configuration and is not editable in the Settings page.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Empty | Model provider API credential |
| `OPENAI_MODEL` | `gpt-5.6` | Provider model identifier |
| `OPENAI_BASE_URL` | Empty | Optional OpenAI-compatible endpoint |
| `OPENAI_API_MODE` | `responses` | `responses` or `chat_completions` |
| `REMOTE_SERVICE_URL` | Empty | Fixed server endpoint used by a client instance |
| `SERVICEPATH_API_TOKEN` | Empty | Shared client-server bearer token |
| `SETTINGS_PASSWORD` | Empty | Protects settings writes |
| `SERVICEPATH_DATA_DIR` | Project paths | Shared settings and database directory |

Secrets written through Settings use an owner-only `.env` file and are never
returned to the browser. Leaving an existing secret field empty keeps its
current value.

## Development

For frontend work:

```bash
npm ci
npm run dev
npm run build
```

Vite serves `http://127.0.0.1:5173` and proxies API calls to Flask on port 5050.
Production assets are generated in `static/frontend/`; rebuild them after each
frontend change and do not edit them by hand.

## Security and limitations

ServicePath rejects literal private, loopback, link-local, and reserved targets.
It validates DNS results before checks and validates each HTTP redirect before
following it. Agent tools cannot change the locked host, URL, port, or command,
and traceroute never invokes a command shell.

These controls are not an operating-system sandbox or a complete SSRF defense.
The HTTP client can resolve an already checked hostname again while connecting,
which leaves a DNS-rebinding race. Production deployments should also enforce
outbound network policy.

ServicePath has no general user authentication or built-in rate limiting.
Diagnosis routes can consume model quota, while reports may expose stored
network evidence. The target and selected evidence are sent to the configured
model provider. Any public deployment must add TLS, authentication,
authorization, request limits, and rate limiting at a reverse proxy. The HTTP
check does not execute page JavaScript, and missing traceroute hops are only
supporting evidence, not proof that normal traffic is blocked.
