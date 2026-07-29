# Repository Guidelines

## Project Structure & Module Organization

`app.py` is the Flask entry point and currently contains the page routes and basic form handling. Jinja templates live in `templates/`; the main page is `templates/index.html`. Browser assets belong in `static/`, with shared styles in `static/style.css`. Dependency declarations are in `requirements.txt`, and setup instructions are maintained in `README.md`.

Place future diagnostic logic in small Python modules rather than growing `app.py` indefinitely. For example, use `diagnostics/dns.py`, `diagnostics/tls.py`, and `diagnostics/http.py`. Put automated tests under `tests/` using names such as `test_routes.py` and `test_dns.py`.

## Build, Test, and Development Commands

Create and activate a local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the development server with `python app.py`, then open `http://127.0.0.1:5050`. Port 5050 is intentional because macOS may reserve port 5000. Run future standard-library tests with:

```bash
python -m unittest discover -s tests
```

## Coding Style & Naming Conventions

Use four spaces for Python indentation and follow PEP 8. Use `snake_case` for functions and variables, `PascalCase` for classes, and short lowercase module names. Keep routes thin: validate input, call a helper, and render or return the result. Use four-space indentation in HTML and keep CSS class names descriptive, such as `.console-card`. No formatter or linter is configured yet, so review diffs for consistency before committing.

## Testing Guidelines

The repository does not yet have an automated test suite. New backend features should include focused `unittest` tests using Flask's test client. Test successful requests, missing or invalid domains, timeouts, and expected error handling. Avoid tests that depend on a specific public website unless clearly marked as integration tests.

## Commit & Pull Request Guidelines

Use Conventional Commit messages already established in history: `feat:`, `fix:`, `style:`, `docs:`, `test:`, `refactor:`, or `chore:`. Make one small, coherent commit per feature or fix. Pull requests should include a short summary, testing performed, linked issue when applicable, and screenshots for visible UI changes.

## Security & Configuration

Keep API keys in `.env`; never commit secrets. Before adding live network diagnostics, validate targets, block private and loopback addresses, recheck redirects, and set strict connection timeouts.
