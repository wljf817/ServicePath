# ServicePath

ServicePath is a Flask and React website-diagnostic application driven by one
OpenAI Agents SDK Agent per execution location. Give it a public HTTP(S) target;
the Agent selects the useful checks, follows the returned evidence, and produces
a structured diagnosis rather than running a fixed five-step script.

The Agent can select from six server-owned tools:

- Client routes and proxy settings
- DNS A/AAAA resolution and public-address validation
- TCP connectivity
- TLS handshake and certificate validation
- HTTP response, redirects, timing, title, and basic CDN/WAF headers
- A short traceroute

Tool prerequisites are collected automatically and cached. For example, asking
for TLS also obtains the DNS and TCP evidence it needs, but each underlying check
runs at most once. The report retains the Agent's selection order, every actual
check, timings, structured fields, raw tool returns, confidence, likely causes,
suggested next actions, and aggregate model/token usage.

If the Agent service fails after tools have already run, ServicePath saves those
results with an explicit low-confidence partial conclusion instead of discarding
the evidence.

## Why an Agent

The OpenAI Agents SDK supplies the tool-use loop: the model chooses a tool,
receives its result, decides whether another check is useful, and finally returns
a typed `AgentDiagnosis`. There are no handoffs or specialist sub-agents.

ServicePath—not the model—owns the safety boundary:

- The target is normalized and locked before the Agent starts.
- Tool schemas accept no hostname, URL, command, port, or shell argument.
- Private, loopback, link-local, and reserved targets are rejected.
- DNS answers and every HTTP redirect are revalidated.
- Connection attempts, response bodies, redirects, traceroute output, Agent
  turns, and unique checks have explicit limits and per-tool timeouts.
- Traceroute is launched with a fixed argument list and never through a shell.
- Agents SDK traces exclude sensitive prompt and tool-return content.

This is a bounded capability layer inside the Flask process, not a replacement
for an operating-system sandbox. A production deployment should still enforce an
outbound firewall or container network policy.

## Execution modes

- **Remote Test:** runs one Agent on the deployed ServicePath server.
- **Local Test:** runs one Agent in a ServicePath instance started on the user's
  computer, so it observes that device and network.
- **Compare Both:** runs the local and remote investigations sequentially and
  compares the evidence each Agent chose to collect.

A normal diagnosis uses at most six unique checks and eight Agent turns. Repeated
tool selections return cached evidence instead of repeating network traffic.

## Project structure

```text
app.py                       Flask pages and JSON routes
database.py                  SQLite report and settings storage
diagnostics/agent.py         Single-Agent runtime and report assembly
diagnostics/agent_models.py  Typed Agent output
diagnostics/agent_tools.py   Locked context, budgets, and Agent tools
diagnostics/                 Network checks and target validation
frontend/                    React 19 and HeroUI v3 source
static/frontend/             Production frontend served by Flask
templates/                   Non-JavaScript fallback/error pages
tests/                       Offline unittest suite
instance/servicepath.db      Local history, created automatically
```

## Install and run

```bash
git clone https://github.com/wljf817/ServicePath.git
cd ServicePath
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set at least the Agent credentials in `.env`:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
```

To use a compatible gateway or local model server, set an optional API base URL
in Settings or `.env`:

```text
OPENAI_BASE_URL=http://127.0.0.1:8000/v1
OPENAI_API_MODE=auto
OPENAI_MODEL=provider-model-name
```

In `auto` mode, the OpenAI default endpoint uses the Responses API and custom
URLs use Chat Completions for broader provider compatibility. Set
`OPENAI_API_MODE=responses` or `OPENAI_API_MODE=chat_completions` to override
that choice. Custom providers must support function tools and JSON output.
Custom endpoints disable Agents SDK tracing for that run.

For DeepSeek, use `https://api.deepseek.com` with `deepseek-v4-flash` or
`deepseek-v4-pro`. The retired `deepseek-chat` and `deepseek-reasoner` names are
rejected with an actionable configuration error.

Then start Flask and open `http://127.0.0.1:5050`:

```bash
python app.py
```

An API key for the selected model provider is required because tool selection
and the final diagnosis are both performed by the Agent. The key and other secrets can also be added from
the Web UI Settings page. They are written to `.env`, never returned to the
browser, and never stored in SQLite.

The target and selected diagnostic evidence are sent to the configured model
provider because they are required for Agent reasoning. Separate Agents SDK
trace spans are configured not to include that sensitive content.

## Frontend development

The production frontend is committed in `static/frontend/`, so Node.js is not
required to run the application. To modify the UI, use a second terminal:

```bash
npm install
npm run dev
```

Keep Flask on port 5050 and open `http://127.0.0.1:5173`. Vite proxies API calls
to Flask. Rebuild committed production assets after a UI change:

```bash
npm run build
```

## Tests

The unit tests mock model and network boundaries, so they do not require an API
key or a particular public website:

```bash
python -m unittest discover -s tests
```

## Settings and remote execution

The Settings page defines the current Flask process as either:

- **Deployed Remote Server:** Remote Test executes on this process.
- **Local Device:** Local Test executes here; Remote Test calls the configured
  deployed ServicePath URL.

For a public remote server, configure both values below. Use the same API token
on the local instance that calls it:

```text
SERVICEPATH_API_TOKEN=choose-a-long-random-token
SETTINGS_PASSWORD=choose-a-strong-password
```

Each execution location needs its own Agent key, model, and optional base URL.
The local instance sends the normalized target to `POST /api/diagnose`; it
verifies that the returned Agent report is for that exact target before comparing
or saving it.

## Known limitations

- The browser receives the report only after the Agent run completes; tool
  events are not streamed yet.
- Traceroute requires `traceroute` on macOS/Linux or `tracert` on Windows and is
  supporting evidence only because intermediate hops often ignore probes.
- Browser JavaScript cannot perform raw DNS, TCP, or TLS checks from a visitor's
  device. Local Test therefore requires a local ServicePath process.
- Client Network reports routes and proxy presence, not public IP, ISP, ASN, or
  geolocation.
- DNS uses the system resolver and does not compare public resolvers or query
  CNAME/WHOIS data.
- Proxy-managed Fake-IP addresses in `198.18.0.0/15` are recognized. Raw TCP/TLS
  checks are skipped in that case and HTTP uses the configured proxy.
- SQLite needs persistent storage. A temporary serverless filesystem loses
  history.
- The remote endpoint supports bearer-token authentication but has no built-in
  rate limiter. Put rate limits and outbound network policy in front of public
  deployments.
