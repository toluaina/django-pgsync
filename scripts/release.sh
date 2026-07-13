#!/usr/bin/env bash
# One-stop release script for django-pgsync.
#
# Usage:
#   scripts/release.sh 0.2.0            # release version 0.2.0
#   scripts/release.sh 0.2.0 --dry-run  # validate everything, change nothing
#
# What it does:
#   1. Preflight: clean tree, on main, synced with origin, gh authenticated,
#      CHANGELOG has a "## <version> (unreleased)" section.
#   2. Bumps __version__, dates the CHANGELOG, commits and pushes.
#   3. Waits for the test workflow to pass on the release commit.
#   4. Publishes GitHub release v<version> with notes from the CHANGELOG,
#      which triggers .github/workflows/release.yml -> PyPI (trusted
#      publishing; no tokens involved).
#   5. Waits for the release workflow and verifies the version on PyPI.
#
# Requirements: git, gh (authenticated), curl, python3. No build tools
# needed locally - CI builds, checks and publishes the artifacts.

set -euo pipefail

REPO="toluaina/django-pgsync"
INIT_FILE="django_pgsync/__init__.py"
CHANGELOG="CHANGELOG.md"

VERSION="${1:-}"
DRY_RUN="${2:-}"

die() { echo "ERROR: $*" >&2; exit 1; }
step() { echo; echo "==> $*"; }

[[ -n "$VERSION" ]] || die "usage: scripts/release.sh <version> [--dry-run]"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must be X.Y.Z, got '$VERSION'"

cd "$(git rev-parse --show-toplevel)"

step "Preflight"
[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean"
[[ "$(git branch --show-current)" == "main" ]] || die "not on main"
git fetch -q origin main
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || die "main is not in sync with origin/main"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated"
grep -q "^## ${VERSION} (unreleased)" "$CHANGELOG" \
    || die "CHANGELOG.md needs a '## ${VERSION} (unreleased)' section describing this release"
! git rev-parse "v${VERSION}" >/dev/null 2>&1 || die "tag v${VERSION} already exists"
CURRENT=$(python3 -c "import re; print(re.search(r'__version__ = \"(.+?)\"', open('$INIT_FILE').read()).group(1))")
echo "current version: ${CURRENT} -> releasing: ${VERSION}"

step "Extract release notes from CHANGELOG"
NOTES=$(python3 - "$VERSION" <<'EOF'
import re, sys
version = sys.argv[1]
text = open("CHANGELOG.md").read()
match = re.search(rf"^## {re.escape(version)} \(unreleased\)\n(.*?)(?=^## |\Z)", text, re.M | re.S)
if not match:
    sys.exit(1)
print(match.group(1).strip())
EOF
)
[[ -n "$NOTES" ]] || die "could not extract release notes for ${VERSION}"
echo "$NOTES" | head -5
echo "..."

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    step "Dry run: all preflight checks passed; no changes made"
    exit 0
fi

step "Bump version and date CHANGELOG"
TODAY=$(date +%Y-%m-%d)
python3 - "$VERSION" <<'EOF'
import re, sys
version = sys.argv[1]
path = "django_pgsync/__init__.py"
src = open(path).read()
src = re.sub(r'__version__ = ".+?"', f'__version__ = "{version}"', src)
open(path, "w").write(src)
EOF
sed -i '' "s/^## ${VERSION} (unreleased)/## ${VERSION} (${TODAY})/" "$CHANGELOG"
git add "$INIT_FILE" "$CHANGELOG"
git commit -m "Release ${VERSION}"
git push

step "Wait for tests on the release commit"
sleep 10
RUN_ID=$(gh run list --repo "$REPO" --workflow test.yml --branch main --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --repo "$REPO" --exit-status

step "Publish GitHub release v${VERSION} (triggers PyPI publish)"
gh release create "v${VERSION}" --repo "$REPO" \
    --title "django-pgsync ${VERSION}" --notes "$NOTES" --latest

step "Wait for the release workflow"
sleep 10
RUN_ID=$(gh run list --repo "$REPO" --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --repo "$REPO" --exit-status

step "Verify on PyPI"
for i in $(seq 1 12); do
    LIVE=$(curl -s "https://pypi.org/pypi/django-pgsync/json" | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])" || true)
    [[ "$LIVE" == "$VERSION" ]] && break
    sleep 10
done
[[ "$LIVE" == "$VERSION" ]] || die "PyPI still shows ${LIVE}; check https://pypi.org/project/django-pgsync/"

echo
echo "Released django-pgsync ${VERSION}"
echo "  https://pypi.org/project/django-pgsync/${VERSION}/"
echo "  https://github.com/${REPO}/releases/tag/v${VERSION}"
echo
echo "Remember: start the next CHANGELOG section as '## X.Y.Z (unreleased)'."
