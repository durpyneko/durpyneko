#!/usr/bin/env bash
# Refresh the profile README from a host that can reach wakapi, and push.
#
# Cloudflare fronts waka.assassin.dev and serves github runners a bot challenge
# (403 text/html) instead of json, so the waka section cannot be produced in CI.
# This runs on a machine whose IP is not challenged. profile.yml still handles
# the PROJECTS and LANGS sections in Actions; only --waka needs to be local.
#
# Config lives in ~/.config/durpy-profile/env (chmod 600):
#     WAKATIME_API_KEY=<raw uuid, not base64>
#     GITHUB_TOKEN=<optional, raises the api rate limit>
set -euo pipefail

REPO="${REPO:-$HOME/Documents/code_repos/durpyneko/durpyneko}"
ENV_FILE="${ENV_FILE:-$HOME/.config/durpy-profile/env}"

if [[ -r "$ENV_FILE" ]]; then
  set -a; . "$ENV_FILE"; set +a
else
  echo "missing $ENV_FILE — cannot authenticate to wakapi" >&2
  exit 1
fi

cd "$REPO"

# never build on top of a dirty tree or a stale main; the push must be a
# fast-forward or this run is a no-op rather than a conflict to untangle later
if [[ -n "$(git status --porcelain)" ]]; then
  echo "working tree dirty — skipping this run" >&2
  exit 0
fi
git fetch --quiet origin main
git checkout --quiet main
git merge --quiet --ff-only origin/main

python3 .github/scripts/update_readme.py --waka

if git diff --quiet -- README.md; then
  echo "no change"
  exit 0
fi

git add README.md
git commit -q -m "chore(readme): refresh wakatime stats"
git push -q origin main
echo "pushed"
