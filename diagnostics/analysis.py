import json
import os


GUIDANCE = {
    "client": {
        "title": "Check the local network environment",
        "explanation": "The first warning or failure appeared in the client network layer.",
        "causes": [
            "No usable network route",
            "IPv6 is unavailable",
            "Proxy settings changed the route",
        ],
        "actions": [
            "Confirm the device is online",
            "Temporarily disable the proxy or VPN",
            "Try another network",
        ],
    },
    "dns": {
        "title": "Investigate DNS resolution",
        "explanation": "The domain could not be resolved to a safe public IP address.",
        "causes": [
            "The domain does not exist",
            "The DNS server is unavailable",
            "The domain points to a private address",
        ],
        "actions": [
            "Check the spelling of the domain",
            "Try a trusted public DNS resolver",
            "Review the domain's DNS records",
        ],
    },
    "tcp": {
        "title": "Check ports and network access",
        "explanation": "DNS worked, but the tested web ports did not accept a TCP connection.",
        "causes": [
            "The web server is offline",
            "A firewall blocks port 80 or 443",
            "The service listens on another port",
        ],
        "actions": [
            "Confirm the web server is running",
            "Review firewall and security-group rules",
            "Verify the configured web port",
        ],
    },
    "tls": {
        "title": "Review HTTPS and certificate settings",
        "explanation": (
            "The network connection worked, but the secure TLS handshake did not "
            "complete normally."
        ),
        "causes": [
            "The certificate is expired or untrusted",
            "The certificate does not match the domain",
            "The server has an incorrect SNI or TLS configuration",
        ],
        "actions": [
            "Renew and install the full certificate chain",
            "Confirm the certificate includes this domain",
            "Review the server's TLS and SNI settings",
        ],
    },
    "http": {
        "title": "Investigate the website application",
        "explanation": (
            "The lower network layers worked, but the website returned an HTTP "
            "warning or server error."
        ),
        "causes": [
            "The application returned an error",
            "A reverse proxy or CDN cannot reach its origin",
            "Access is denied or the page is missing",
        ],
        "actions": [
            "Review the HTTP status and server logs",
            "Check the application and upstream services",
            "Verify CDN or reverse-proxy configuration",
        ],
    },
}


def rule_based_analysis(report):
    problem = report.get("first_problem")

    if not problem:
        return {
            "source": "rules",
            "title": "No failure was detected",
            "explanation": "All five diagnostic layers passed from this test location.",
            "causes": [],
            "actions": [
                "No repair is required based on this test.",
                "If the problem is intermittent, run another test when it happens.",
            ],
        }

    guidance = GUIDANCE[problem].copy()
    guidance["source"] = "rules"
    return guidance


def request_openai_analysis(report):
    from openai import OpenAI

    model = os.getenv("OPENAI_MODEL", "gpt-5.6")
    prompt = (
        "You are a website reliability assistant. Analyze the JSON diagnostic report below. "
        "Use only the supplied evidence. State the most likely fault layer and uncertainty. "
        "Then give short, prioritized actions for a normal visitor and for a website owner. "
        "Do not claim that a guess is proven. Keep the answer under 250 words.\n\n"
        + json.dumps(report, indent=2)
    )
    client = OpenAI()
    response = client.responses.create(model=model, input=prompt)

    return {
        "source": "openai",
        "model": model,
        "text": response.output_text,
    }


def analyze_report(report):
    fallback = rule_based_analysis(report)

    if not os.getenv("OPENAI_API_KEY"):
        return fallback

    try:
        return request_openai_analysis(report)
    except Exception:
        fallback["note"] = (
            "AI analysis was unavailable, so rule-based guidance was used instead."
        )
        return fallback
