# Releasing django-pgsync

Releases are fully automated via PyPI trusted publishing — no tokens, no
local build tools. CI builds, `twine check`s and uploads the artifacts
when a GitHub release is published.

## The short version

1. Make sure `CHANGELOG.md` has a section for the new version:

   ```markdown
   ## 0.2.0 (unreleased)

   - What changed...
   ```

2. Run:

   ```bash
   scripts/release.sh 0.2.0            # or --dry-run first to validate
   ```

That's it. The script bumps `__version__`, dates the changelog, commits,
pushes, waits for tests, publishes the GitHub release (which triggers the
PyPI upload), and verifies the new version is live on PyPI.

## What the automation relies on

- **`.github/workflows/release.yml`** — builds and publishes on the
  `release: published` event. Run it manually from the Actions tab
  (workflow_dispatch) for a dry-run build that skips publishing.
- **PyPI trusted publisher** — registered on pypi.org for project
  `django-pgsync`, repo `toluaina/django-pgsync`, workflow `release.yml`,
  environment `pypi`. Nothing is stored in the repo.
- **`pypi` GitHub environment** — restricted to `v*` tag deployments, so
  only real releases can reach the publishing credentials.

## Manual fallback

If the script is unavailable, the steps it automates:

```bash
# 1. bump __version__ in django_pgsync/__init__.py
# 2. change "## X.Y.Z (unreleased)" to "## X.Y.Z (YYYY-MM-DD)" in CHANGELOG.md
git commit -am "Release X.Y.Z" && git push
# 3. wait for CI, then:
gh release create vX.Y.Z --title "django-pgsync X.Y.Z" --notes "<changelog section>" --latest
# 4. the release workflow publishes to PyPI; verify:
curl -s https://pypi.org/pypi/django-pgsync/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

A failed publish burns nothing — no version lands on PyPI, and the
workflow can be re-run from the Actions tab after fixing.
