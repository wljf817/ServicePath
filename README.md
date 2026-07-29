# ServicePath

ServicePath is a Flask website diagnostic tool with a React and HeroUI frontend. Enter a domain or HTTP(S) URL and it checks five layers in order:

1. Client network routes and proxy settings
2. DNS A and AAAA resolution
3. TCP connectivity on ports 80 and 443
4. TLS handshake, certificate trust, expiration, and hostname match
5. HTTP status, redirects, response time, page title, and basic CDN/WAF headers

ServicePath also runs a supplemental Traceroute between DNS and TCP. It records up to eight hops, the executed command, return code, timing, and raw output without changing the five-layer fault classification.

Every check reports **Passed**, **Warning**, **Error**, or **Skipped**. The console expands each check into its timing and returned sub-check values. ServicePath identifies the first problem layer. An OpenAI API key enables AI-generated analysis; without a key, the report lists detected warnings and errors without generating advice.

The interface has three modes:

- **Remote Test:** runs directly on the deployed ServicePath server. This is the default mode.
- **Local Test:** runs from a ServicePath instance started on the user's computer.
- **Compare Both:** is available from the local instance and classifies the result as local-only, remote-only, shared, different, or no issue.

## Project structure

```text
app.py                 Flask routes and JSON API
database.py            SQLite report storage
diagnostics/           Target validation and five diagnostic layers
frontend/              React 19 and HeroUI v3 source
static/frontend/       Production frontend build served by Flask
templates/             Fallback Jinja error pages
tests/                  unittest test suite
instance/servicepath.db Local diagnostic history (created automatically)
```

## Install and run

```bash
git clone https://github.com/wljf817/ServicePath.git
cd ServicePath
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5050`. Port 5050 avoids a common macOS conflict on port 5000.

The production frontend is committed in `static/frontend/`, so Node.js is not required just to run the app. To change the UI, install the frontend dependencies and run the Vite development server in a second terminal:

```bash
npm install
npm run dev
```

Keep Flask running on port 5050 and open `http://127.0.0.1:5173`. Vite forwards API requests to Flask. After frontend changes, create the production assets with:

```bash
npm run build
```

Run the tests with:

```bash
python -m unittest discover -s tests
```

## Optional AI analysis

Add an API key from the WebUI Settings page or directly in `.env`:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
```

Keys are read from the environment and `.env` is ignored by Git. The integration uses the OpenAI Responses API. If the API is unavailable, diagnostics still complete, but no analysis or repair advice is generated.

## Settings and execution location

Open `/settings` to choose the role of the current Flask process:

- **Deployed Remote Server:** Remote Test runs on the current server. This is the default and recommended role for the hosted website.
- **Local Device:** Local Test runs on the current computer. Enter the deployed server URL to enable Remote Test and Compare Both.

The same page can configure the Remote API token, OpenAI API key and model, and Settings password. New secrets are written to `.env` with owner-only file permissions. Existing secret values are never returned to the browser; leaving a secret field blank keeps its current value.

On a public deployment, set an administrator password before changing settings:

```text
SETTINGS_PASSWORD=choose-a-strong-password
```

Localhost can update settings without a password. API keys and tokens are never stored in the settings database.

## Connect a local instance to the deployed server

On the deployed server, set:

```text
SERVICEPATH_API_TOKEN=choose-a-long-random-token
SETTINGS_PASSWORD=choose-a-strong-password
```

On the user's computer, start ServicePath, open Settings, select **Local Device**, and enter the deployed URL. Set the same token in the local `.env`:

```text
SERVICEPATH_API_TOKEN=choose-a-long-random-token
```

The local instance calls `POST /api/diagnose` on the deployed server. Compare Both stores the two complete reports, a five-layer side-by-side comparison, and one combined analysis in SQLite.

## Course requirements completed

- **Persistent data store:** SQLite reports are created and read in `database.py`.
- **Meaningful POST:** `POST /diagnose` runs local, remote, or comparison diagnostics, analyzes the result, saves it, and redirects to a report. `POST /api/diagnose` runs remote checks.
- **Public hosting:** deployment is supported but no live deployment is included in this repository yet.

## Known limitations

- Console lines appear when the request finishes; they are not streamed live.
- Traceroute requires the system `traceroute` command on macOS/Linux or `tracert` on Windows. It is skipped when unavailable, after DNS failure, or when proxy DNS returns a synthetic Fake-IP.
- Compare Both runs Local Test and Remote Test one after the other, so it takes longer than either individual mode.
- A deployed webpage cannot perform raw DNS, TCP, or TLS checks from a visitor's device. Local Test and Compare Both therefore require the user to start the local Flask instance.
- When the machine running a test has a system proxy, ServicePath recognizes Fake-IP DNS in `198.18.0.0/15`. It skips misleading raw TCP/TLS checks and runs HTTP through that proxy.
- Client Network reports local routes and proxy presence, not public IP, ISP, ASN, or location.
- DNS uses the system resolver and does not yet compare public resolvers or query CNAME/WHOIS data.
- SQLite requires a persistent filesystem when deployed; a temporary serverless filesystem will lose history.
- The remote API has optional token authentication but no rate limiting. Configure a token before public deployment.
- ServicePath blocks private/reserved targets and rechecks redirects, but production deployments should also enforce outbound network rules.
