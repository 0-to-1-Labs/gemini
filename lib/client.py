"""
Shared Gemini client for every skill in the plugin.

Handles the three things every script needs: the google-genai dependency
(installed into a private virtual environment on first run), the API key,
and readable error messages.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

# The Interactions API needs google-genai 2.3.0 or later.
GENAI_PACKAGE = "google-genai>=2.3.0"
API_KEY_URL = "https://aistudio.google.com/apikey"
MIN_PYTHON = (3, 10)

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = PLUGIN_ROOT / "requirements.txt"
# Claude Code substitutes ${CLAUDE_PLUGIN_DATA} in skill text but does not
# export it to Bash commands, so the cache directory is the usual location.
DATA_DIR = Path(
    os.getenv("CLAUDE_PLUGIN_DATA") or Path.home() / ".cache" / "claude-gemini-plugin"
).expanduser()
VENV_DIR = DATA_DIR / "venv"
_REEXEC_MARKER = "GEMINI_PLUGIN_REEXEC"


def fail(message, hints=None):
    """Print an error (and optional hints) and exit with status 1."""
    print(f"ERROR: {message}")
    if hints:
        print("\nPossible causes:")
        for hint in hints:
            print(f"  - {hint}")
    sys.exit(1)


def _venv_python():
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _in_venv():
    return Path(sys.prefix).resolve() == VENV_DIR.resolve()


def _run(cmd):
    """Run a command, showing its output. Return True on success."""
    return subprocess.run(cmd).returncode == 0


def _exec_venv():
    """Re-run the current script with the private venv's interpreter."""
    python = _venv_python()
    os.environ[_REEXEC_MARKER] = "1"
    sys.stdout.flush()  # exec discards Python's buffers, so push output first.
    sys.stderr.flush()
    os.execv(str(python), [str(python), *sys.argv])


def bootstrap_venv():
    """Create the private venv, install requirements, and re-exec into it.

    Never touches the system or Homebrew Python. The venv lives under
    $CLAUDE_PLUGIN_DATA when that is set, else ~/.cache/claude-gemini-plugin.
    """
    if sys.version_info < MIN_PYTHON:
        fail(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is required "
             f"(found {sys.version.split()[0]} at {sys.executable}).")
    python = _venv_python()
    if not python.exists():
        print(f"First run: creating a private Python environment at {VENV_DIR} "
              f"and installing {REQUIREMENTS.name}...")
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        if not _run([sys.executable, "-m", "venv", str(VENV_DIR)]):
            fail(f"Could not create a virtual environment at {VENV_DIR}.",
                 ["Your Python may lack the venv module (Debian: apt install python3-venv)"])
        if not _run([str(python), "-m", "pip", "install", "--quiet",
                     "-r", str(REQUIREMENTS)]):
            fail(f"Could not install {REQUIREMENTS} into {VENV_DIR}.",
                 ["Network or PyPI is unreachable",
                  f"Delete {VENV_DIR} and re-run to start over"])
    _exec_venv()


def ensure(import_callable, package):
    """Return the result of import_callable(), installing `package` if needed.

    Missing packages go into the plugin's private venv, never into the
    interpreter that launched the script. Outside the venv, a missing import
    re-runs the script inside the venv (creating it on first run), so call this
    before any output or API call.
    """
    try:
        return import_callable()
    except ImportError:
        pass
    if not _in_venv():
        if os.getenv(_REEXEC_MARKER):
            fail(f"'{package}' is still not importable after switching to {VENV_DIR}.",
                 [f"Delete {VENV_DIR} and re-run to rebuild it"])
        bootstrap_venv()
    print(f"Installing '{package}' into {VENV_DIR}...")
    if not _run([sys.executable, "-m", "pip", "install", "--quiet", package]):
        fail(f"Could not install '{package}' into {VENV_DIR}.",
             ["Network or PyPI is unreachable",
              f"Install it by hand: {_venv_python()} -m pip install '{package}'"])
    importlib.invalidate_caches()
    try:
        return import_callable()
    except ImportError as e:
        fail(f"Installed '{package}', but it is not importable in {sys.executable}: {e}",
             [f"Delete {VENV_DIR} and re-run to rebuild it"])


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
    key = api_key()  # Check the key before any dependency install.
    genai, _ = genai_modules()
    client = genai.Client(api_key=key)
    if not hasattr(client, "interactions"):
        print("ERROR: The installed google-genai package is too old for this plugin.")
        print(f"\nUpgrade it with:\n  {sys.executable} -m pip install --upgrade '{GENAI_PACKAGE}'")
        sys.exit(1)
    return client


def _redact(text):
    """Blank out the API key if an error message happens to include it."""
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.getenv(name)
        if key and key in text:
            text = text.replace(key, "[redacted]")
    return text


def explain_error(error, model=None, fallback_hint=None):
    """Print an API error with hints matched to the message, then return None."""
    print(f"ERROR: Request failed: {_redact(str(error))}")
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
