"""Organization-controlled provider selection for trusted review runners."""
import os
import re

def configure(settings):
    for provider in ("codex", "claude"):
        for field in ("model", "effort"):
            name = f"{provider.upper()}_REVIEW_{field.upper()}"
            value = os.environ.get(name, "")
            pattern = r"[A-Za-z0-9][A-Za-z0-9._-]*" if field == "model" else r"[a-z]+"
            if not re.fullmatch(pattern, value):
                raise ValueError(f"Configure organization Actions variable {name} for this repository")
            settings[provider][field] = value
    return settings
