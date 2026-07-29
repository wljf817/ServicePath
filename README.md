# ServicePath

ServicePath is a Flask website diagnostic tool. Enter a domain or HTTP(S) URL and it checks five layers in order:

1. Client network routes and proxy settings
2. DNS A and AAAA resolution
3. TCP connectivity on ports 80 and 443
4. TLS handshake, certificate trust, expiration, and hostname match
5. HTTP status, redirects, response time, page title, and basic CDN/WAF headers

Every layer reports **Passed**, **Warning**, **Error**, or **Skipped**. ServicePath identifies the first problem layer and produces repair guidance. An OpenAI API key enables AI-generated analysis; without a key, the app uses built-in rule-based guidance.

## Project structure

```text
app.py                 Flask routes
database.py            SQLite report storage
diagnostics/           Target validation and five diagnostic layers
templates/             Jinja pages
static/                 CSS and small loading-state script
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

Run the tests with:

```bash
python -m unittest discover -s tests
```

## Optional AI analysis

Add an API key to `.env`:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
```

Keys are read from the environment and `.env` is ignored by Git. The integration uses the OpenAI Responses API. If the API is unavailable, diagnostics still complete with rule-based guidance.

## Remote Test setup

Deploy a second ServicePath instance, then configure the local instance:

```text
REMOTE_SERVICE_URL=https://your-servicepath-server.example
SERVICEPATH_API_TOKEN=choose-a-long-random-token
```

Set the same `SERVICEPATH_API_TOKEN` on the remote instance. Remote Test calls `POST /api/diagnose`; the target checks run from the deployed server, while the returned report is analyzed and saved by the local app.

## Course requirements completed

- **Persistent data store:** SQLite reports are created and read in `database.py`.
- **Meaningful POST:** `POST /diagnose` runs diagnostics, analyzes the result, saves it, and redirects to a report. `POST /api/diagnose` runs remote checks.
- **Public hosting:** deployment is supported but no live deployment is included in this repository yet.

## Known limitations

- Console lines appear when the request finishes; they are not streamed live.
- Client Network reports local routes and proxy presence, not public IP, ISP, ASN, or location.
- DNS uses the system resolver and does not yet compare public resolvers or query CNAME/WHOIS data.
- SQLite requires a persistent filesystem when deployed; a temporary serverless filesystem will lose history.
- The remote API has optional token authentication but no rate limiting. Configure a token before public deployment.
- ServicePath blocks private/reserved targets and rechecks redirects, but production deployments should also enforce outbound network rules.
