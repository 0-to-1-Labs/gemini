"""
Shared Gemini client for every skill in the plugin.

Handles the three things every script needs: the google-genai dependency
(auto-installed on first run), the API key, and readable error messages.
"""

import importlib
import os
import subprocess
import sys

# The Interactions API needs google-genai 2.3.0 or later.
GENAI_PACKAGE = "google-genai>=2.3.0"
API_KEY_URL = "https://aistudio.google.com/apikey"


def fail(message, hints=None):
    """Print an error (and optional hints) and exit with status 1."""
    print(f"ERROR: {message}")
    if hints:
        print("\nPossible causes:")
        for hint in hints:
            print(f"  - {hint}")
    sys.exit(1)


def _pip_install(package):
    """Install a package, trying strategies that work in externally-managed envs."""
    for extra in (["--user"], ["--break-system-packages"], []):
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", *extra, package],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            continue
    return False


def ensure(import_callable, package):
    """Return the result of import_callable(), auto-installing `package` if needed.

    Installs and re-imports in the same process so the user never has to re-run
    the command after a first-time dependency install.
    """
    try:
        return import_callable()
    except ImportError:
        print(f"Required package '{package}' is not installed. Installing...")
        if not _pip_install(package):
            print(f"\nERROR: Failed to auto-install '{package}'.")
            print("\nPlease install it manually with one of:")
            print(f"  pip install --user '{package}'")
            print(f"  pip install --break-system-packages '{package}'")
            print("\nOr use a virtual environment:")
            print("  python3 -m venv venv && source venv/bin/activate")
            print(f"  pip install '{package}'")
            sys.exit(1)
        importlib.invalidate_caches()
        try:
            return import_callable()
        except ImportError as e:
            print(f"\nInstalled '{package}', but it is not importable in this "
                  f"interpreter ({sys.executable}).")
            print(f"Import error: {e}")
            print("If you use a virtualenv or pyenv, install it there and re-run.")
            print(f"If the error mentions architecture, run: "
                  f"pip install --user --force-reinstall '{package}'")
            sys.exit(1)


def _import_genai():
    from google import genai
    from google.genai import types
    return genai, types


def genai_modules():
    """Return (genai, types), installing google-genai on first use."""
    return ensure(_import_genai, GENAI_PACKAGE)


def api_key():
    """Return the Gemini API key from the environment, or exit with guidance."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("\nTo fix this, set your API key:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print(f"\nGet your API key at: {API_KEY_URL}")
        sys.exit(1)
    return key


def get_client():
    """Return a google-genai Client that supports the Interactions API."""
    genai, _ = genai_modules()
    client = genai.Client(api_key=api_key())
    if not hasattr(client, "interactions"):
        print("ERROR: The installed google-genai package is too old for this plugin.")
        print(f"\nUpgrade it with:\n  pip install --upgrade '{GENAI_PACKAGE}'")
        sys.exit(1)
    return client


def explain_error(error, model=None, fallback_hint=None):
    """Print an API error with hints matched to the message, then return None."""
    print(f"ERROR: Request failed: {error}")
    text = str(error).lower()
    if "api key" in text or "authentication" in text or "unauthenticated" in text:
        hints = [
            "Invalid API key",
            "API key not properly set in GEMINI_API_KEY environment variable",
            "API key may have been revoked or expired",
        ]
    elif "quota" in text or "rate limit" in text or "resource_exhausted" in text:
        hints = [
            "API quota exceeded",
            "Rate limit reached",
            "This model may have no free tier; check billing at " + API_KEY_URL,
            "Try again in a few moments",
        ]
    elif "not found" in text or "model" in text:
        hints = [f"The model '{model}' is not available to your API key/region"]
        if fallback_hint:
            hints.append(fallback_hint)
    elif "network" in text or "connection" in text:
        hints = [
            "Network connectivity issues",
            "Firewall blocking API requests",
            "Check your internet connection",
        ]
    else:
        hints = None
    if hints:
        print("\nPossible causes:")
        for hint in hints:
            print(f"  - {hint}")
    return None


def output_text(interaction):
    """Return the text output of an interaction, or an empty string."""
    return getattr(interaction, "output_text", None) or ""
