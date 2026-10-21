"""Owner OAuth for the fixed Drive backup; secrets stay outside the project.

Windows DPAPI binds saved credentials to the current Windows account. No token
or client secret is printed. The loopback flow uses Google's library and PKCE.
"""
import argparse
import contextlib
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path

SCOPE = "https://www.googleapis.com/auth/drive"
PRIVATE = Path.home() / ".llm-pj-backup"
TOKEN = PRIVATE / "owner-oauth.dpapi"


def protect(data, decrypt=False):
    if os.name != "nt":
        raise RuntimeError("Windows DPAPI is required; no plaintext fallback")

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    method = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    method.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                       wintypes.DWORD, ctypes.POINTER(Blob)]
    method.restype = wintypes.BOOL
    if not method(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


def save_credentials(credentials):
    PRIVATE.mkdir(exist_ok=True)
    temporary = TOKEN.with_suffix(".pending")
    temporary.write_bytes(protect(credentials.to_json().encode("utf-8")))
    temporary.replace(TOKEN)


def session():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request
    if not TOKEN.exists():
        raise RuntimeError("Owner consent not completed; no Drive credential saved")
    data = json.loads(protect(TOKEN.read_bytes(), decrypt=True))
    if SCOPE not in data.get("scopes", []):
        raise RuntimeError("Owner Drive scope missing")
    credentials = Credentials.from_authorized_user_info(data, scopes=[SCOPE])
    if not credentials.valid:
        credentials.refresh(Request())
        save_credentials(credentials)
    return AuthorizedSession(credentials)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-json", type=Path, required=True)
    args = parser.parse_args()
    from google_auth_oauthlib.flow import InstalledAppFlow
    raw = args.client_json.read_bytes()
    client = json.loads(protect(raw, decrypt=True) if args.client_json.suffix == ".dpapi" else raw)
    installed = client.get("installed", {})
    if (installed.get("auth_uri") != "https://accounts.google.com/o/oauth2/auth"
            or installed.get("token_uri") != "https://oauth2.googleapis.com/token"):
        raise ValueError("Expected a Google Desktop OAuth client")
    PRIVATE.mkdir(exist_ok=True)
    flow = InstalledAppFlow.from_client_config(
        client, scopes=[SCOPE], autogenerate_code_verifier=True)
    # The URL includes OAuth state. Keep it local; never commit it or log tokens.
    with (PRIVATE / "authorization-url.txt").open("w", encoding="utf-8", buffering=1) as stream:
        with contextlib.redirect_stdout(stream):
            credentials = flow.run_local_server(
                host="127.0.0.1", port=0, open_browser=False,
                authorization_prompt_message="{url}", timeout_seconds=600,
                success_message="LLM_PJ authorization received. You may close this tab.")
    if not credentials.refresh_token:
        raise RuntimeError("Offline authorization missing; credential not saved")
    save_credentials(credentials)
    print(json.dumps({"credential_saved": True, "storage": "Windows DPAPI",
                      "backup_started": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # OAuth exception strings can include redirect URLs or authorization data.
        print(json.dumps({"credential_saved": False, "error_type": type(error).__name__,
                          "backup_started": False}))
        raise SystemExit(1) from None
