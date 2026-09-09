import os

import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def send_discord_notification(title: str, body: str) -> bool:
    if not DISCORD_WEBHOOK_URL:
        print(f"[discord disabled] {title}\n{body}")
        return False

    content = f"**{title}**\n```\n{body[:1800]}\n```"
    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=10)
    return resp.status_code in (200, 204)
