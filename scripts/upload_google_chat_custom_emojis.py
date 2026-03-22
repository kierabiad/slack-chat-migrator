import base64
import json
import os
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/chat.customemojis"]

CLIENT_SECRET_FILE = "oauth_client_secret.json"
TOKEN_FILE = "token_custom_emoji.json"

EMOJI_DIR = Path("custom_emojis")
OUTPUT_MAP = Path("custom_emoji_map.json")


def get_creds():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds


def upload_custom_emoji(access_token: str, filepath: Path):
    with open(filepath, "rb") as f:
        raw = f.read()

    body = {
        "emojiName": f":{filepath.stem}:",
        "payload": {
            "fileContent": base64.b64encode(raw).decode("utf-8"),
            "filename": filepath.name,
        },
    }

    response = requests.post(
        "https://chat.googleapis.com/v1/customEmojis",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=120,
    )

    if response.status_code >= 300:
        raise RuntimeError(f"{filepath.name}: {response.status_code} {response.text}")

    return response.json()


def main():
    if not EMOJI_DIR.exists():
        raise FileNotFoundError(f"Missing folder: {EMOJI_DIR}")

    creds = get_creds()
    token = creds.token

    mapping = {}

    files = sorted([p for p in EMOJI_DIR.iterdir() if p.is_file()])
    print(f"Found {len(files)} emoji files in {EMOJI_DIR}")

    for filepath in files:
        shortcode = filepath.stem
        try:
            result = upload_custom_emoji(token, filepath)
            mapping[shortcode] = result["name"]
            print(f"Uploaded: {shortcode} -> {result['name']}")
        except Exception as e:
            print(f"FAILED: {shortcode} -> {e}")

    with open(OUTPUT_MAP, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print(f"\nSaved mapping to {OUTPUT_MAP}")


if __name__ == "__main__":
    main()