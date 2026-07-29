# ServicePath

ServicePath is a Flask-based website diagnostic tool that checks where a connection problem occurs.

It performs five layers of diagnostics:

- Client network
- DNS
- TCP/network connectivity
- TLS and certificates
- HTTP/application response

Each check reports `Passed`, `Warning`, or `Error`. The structured results can then be sent to an AI service to explain likely causes and suggest practical fixes.

## Planned features

- Local and remote diagnostic modes
- Live diagnostic console
- SQLite diagnostic history
- AI-assisted explanations and recommendations

## Technology

Python, Flask, SQLite, HTML, CSS, JavaScript, and an AI API.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5050` in your browser.

## Status

The first version of the user interface is complete. Diagnostic logic will be added next.
