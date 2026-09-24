"""Bound complete review prompts without claiming bytes are model tokens."""


def validate_capacity(settings):
    maximum = settings["maximum_context_bytes"]
    window = settings["codex"]["context_window_tokens"]
    compact = settings["codex"]["auto_compact_token_limit"]
    if type(maximum) is not int or not 0 < maximum <= 2 * 1024 * 1024:
        raise ValueError("Review input must have a positive bound at most 2 MiB")
    # The inspected OAuth catalog advertises max_context_window=872000, 95% effective.
    # Reserve at least 128000 tokens below that effective window; do not forge metadata.
    if (type(window) is not int or not 0 < window <= 872000
            or type(compact) is not int or not 0 < compact <= window * 95 // 100 - 128000):
        raise ValueError("Codex capacity must retain its catalog bound and output reserve")


def require_context_size(content, maximum):
    if type(maximum) is not int or not 0 < maximum <= 2 * 1024 * 1024:
        raise ValueError("Invalid complete review context byte bound")
    if len(content) > maximum:
        raise ValueError("Review context exceeds the configured bound; no content was silently omitted")
