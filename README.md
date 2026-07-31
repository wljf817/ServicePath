# ServicePath

ServicePath is an AI-assisted website connectivity diagnostic tool. It gives a
bounded Agent read-only network tools, streams tool calls and evidence to the
browser, and produces a validated report covering the observed failure layer,
confidence, causes, and next actions.

Reports and user settings are stored only in the current browser with
IndexedDB. The server does not store history, user API keys, custom-server
tokens, or browser settings.

## Checks

| Stage | Evidence |
| --- | --- |
| Client | IPv4/IPv6 route availability and proxy detection |
| DNS | A/AAAA, CNAME, NS, SOA, TTL, DNSSEC, and public-address validation |
| Route | Optional `traceroute` or `tracert` |
| TCP | Independent IPv4 and IPv6 connections to the target port |
| TLS | Per-family trust, hostname, protocol, cipher, and expiry |
| HTTP | Redirects, protocol, ALPN, timing, content, and CDN/WAF signals |

Targets are normalized and locked before execution. Agent tools cannot change
the target, and invalid configuration or unsupported conclusions stop the run
without saving a report. There are no retries, fallbacks, or automatic server
switches.

## Local setup

Requirements: Python 3.10+, an OpenAI-compatible model with tool calling and
JSON output, and `traceroute` on macOS/Linux or `tracert` on Windows.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5050`. Settings separates model providers from remote
ServicePath servers; custom values are private to the current browser.
Node.js is required only when changing the React frontend:

```bash
npm ci
npm run build
```

## Server presets

The server can provide private model and remote-server presets from
`servicepath.config.json`.
Copy `servicepath.config.example.json`, keep the resulting file out of Git, and
set restrictive file permissions.

```json
{
  "server_token": "shared_custom_server_token",
  "models": [
    {
      "id": "deepseek-v4-pro",
      "name": "DeepSeek V4 Pro",
      "api_key": "private_provider_key",
      "model": "deepseek-v4-pro",
      "base_url": "https://api.deepseek.com",
      "api_mode": "chat_completions"
    },
    {
      "id": "deepseek-v4-flash",
      "name": "DeepSeek V4 Flash",
      "api_key": "private_provider_key",
      "model": "deepseek-v4-flash",
      "base_url": "https://api.deepseek.com",
      "api_mode": "chat_completions"
    }
  ],
  "servers": [
    {
      "id": "new-york",
      "name": "New York",
      "url": "https://nyc.servicepath.example",
      "token": "private_remote_server_token"
    }
  ]
}
```

Start with a custom path when needed:

```bash
SERVICEPATH_CONFIG=/secure/servicepath.config.json python app.py
```

The browser receives only public preset metadata. Model API keys, remote-server
tokens, and the inbound server token are never returned. A server preset appears
directly in the **Run from** list.

## Custom ServicePath server

Set `server_token` in the remote instance's private configuration. In the
calling instance, add its URL and token to the `servers` list, or save them in
the browser under Settings for a one-browser custom server. Remote Agent tool
events are streamed live. The remote instance resolves its own model preset
IDs; matching IDs must therefore exist there, or the user can select a custom
provider.

## Docker

Copy the example configuration before adding secrets:

```bash
cp servicepath.config.example.json servicepath.config.json
sudo chown root:10001 servicepath.config.json
sudo chmod 640 servicepath.config.json
sudoedit servicepath.config.json
```

The image runs as UID/GID `10001`. Keeping the file owned by `root`, readable
by group `10001`, and inaccessible to everyone else lets the unprivileged
container read it without exposing provider keys to other host users. Apply
the same ownership and mode after replacing the file.

Set its host path in `.env`:

```dotenv
SERVICEPATH_CONFIG_FILE=./servicepath.config.json
SERVICEPATH_BIND_ADDRESS=127.0.0.1
SERVICEPATH_PORT=5050
```

Then deploy:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f servicepath
```

The container runs as an unprivileged user with a read-only root filesystem,
dropped capabilities, and a `/healthz` check. There is no application data
volume because history and user settings remain in each browser.

## Public deployment

Use HTTPS. Browser-stored API keys are transmitted to the selected ServicePath
server only for the active diagnosis and are never written to disk by the
application. They are still accessible to JavaScript on the same origin, so a
strong Content Security Policy and XSS prevention remain essential.

ServicePath has no built-in user authentication or rate limiting. A public
reverse proxy must provide TLS, authentication where required, rate limiting,
request limits, and a timeout of at least five minutes. Apply outbound network
policy as an additional SSRF boundary. Reports disappear when users clear site
data and do not sync between browsers or devices.
