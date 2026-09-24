#!/usr/bin/env bash
set -euo pipefail

test "$RUNNER_KIND" = github-hosted
current_userns="$(sysctl -n kernel.unprivileged_userns_clone 2>/dev/null || true)"
if [ -n "$current_userns" ] && [ "$current_userns" != 1 ]; then
  sudo sysctl -w kernel.unprivileged_userns_clone=1
fi
current_apparmor="$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || true)"
if [ -n "$current_apparmor" ] && [ "$current_apparmor" != 0 ]; then
  sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0
fi
