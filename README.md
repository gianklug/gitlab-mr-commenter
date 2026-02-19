# gitlab-mr-commenter

Post and **idempotently update** comments on GitLab merge requests.

Re-running with the same `comment_id` updates the existing note in place rather
than creating a duplicate — useful for plan/apply pipelines where you want a
single, always-current comment per environment.

Inspired by the `mr-commenter` sub-command in
[`gitlab-tofu-ctl`](https://gitlab.com/components/opentofu), reimplemented as a
standalone Python package with both a library API and a CLI.

---

## Installation

```bash
# Add to a project
uv add gitlab-mr-commenter

# Run without installing (ephemeral)
uvx gitlab-mr-commenter --help

# pip also works
pip install gitlab-mr-commenter
```

Python 3.9+ is required. The only dependency is
[`python-gitlab`](https://python-gitlab.readthedocs.io/) ≥ 8.0.

---

## Quick start

### CLI

```bash
# Content is read from stdin; IDs and token are read from CI environment variables.
echo "## Plan: no changes" | gitlab-mr-commenter plan-production

# Explicit flags override env vars.
echo "## Plan: no changes" | gitlab-mr-commenter \
  --project-id 123 \
  --mr-iid 45 \
  --token "$GITLAB_TOKEN" \
  --api-url "https://gitlab.com/api/v4" \
  plan-production
```

### Python

```python
from gitlab_mr_commenter import MRCommenter

commenter = MRCommenter()          # reads token + URL from env
commenter.post(
    project_id=123,
    mr_iid=45,
    comment_id="plan-production",
    content="## Plan\n\nNo changes.",
)
```

One-shot convenience function:

```python
from gitlab_mr_commenter import post_comment

post_comment(123, 45, "plan-production", "## Plan\n\nNo changes.")
```

---

## Configuration

All configuration can be supplied either as keyword arguments (library) / CLI
flags, or via environment variables. Environment variables are the natural
choice in CI pipelines.

| Environment variable | CLI flag | Description |
|---|---|---|
| `GITLAB_MR_PLAN_TOKEN` | `--token` | GitLab API token (preferred) |
| `GITLAB_TOKEN` | `--token` | GitLab API token (fallback) |
| `CI_API_V4_URL` | `--api-url` | GitLab API base URL, e.g. `https://gitlab.com/api/v4` |
| `CI_PROJECT_ID` | `--project-id` | Numeric project ID |
| `CI_MERGE_REQUEST_IID` | `--mr-iid` | MR internal (project-scoped) ID |

> **Token scopes** — the token needs at least the `api` scope (or
> `write_repository` for project tokens). In GitLab CI, a
> [project access token](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html)
> with **Developer** role and `api` scope is sufficient.

---

## How it works

Each managed comment has a hidden HTML marker appended to its body:

```
<!-- gitlab-mr-commenter id="plan-production" -->
```

On every run the tool paginates through all notes on the MR looking for this
marker. If found, the note is updated in place. If not found, a new note is
created. The marker format is compatible with `gitlab-tofu-ctl mr-commenter`
so both tools can coexist on the same MR.

---

## CLI reference

```
usage: gitlab-mr-commenter [-h] [--project-id ID] [--mr-iid IID]
                           [--token TOKEN] [--api-url URL]
                           COMMENT_ID

positional arguments:
  COMMENT_ID         Unique name for this comment slot, e.g. 'plan-production'.
                     A second run with the same value updates the existing comment.

options:
  -h, --help         show this help message and exit
  --project-id ID    GitLab project ID. Defaults to $CI_PROJECT_ID.
  --mr-iid IID       MR internal ID. Defaults to $CI_MERGE_REQUEST_IID.
  --token TOKEN      GitLab API token. Defaults to $GITLAB_MR_PLAN_TOKEN
                     or $GITLAB_TOKEN.
  --api-url URL      GitLab API base URL. Defaults to $CI_API_V4_URL.
```

---

## Development setup

```bash
git clone https://github.com/your-org/gitlab-mr-commenter
cd gitlab-mr-commenter

# Install dependencies (creates .venv automatically)
uv sync

# Run the CLI
uv run gitlab-mr-commenter --help
```

### Running the CLI locally against a real MR

```bash
export GITLAB_MR_PLAN_TOKEN="glpat-xxxxxxxxxxxx"
export CI_API_V4_URL="https://gitlab.com/api/v4"
export CI_PROJECT_ID="12345678"
export CI_MERGE_REQUEST_IID="42"

echo "## Test comment $(date)" | uv run gitlab-mr-commenter test-local
```

---

## Publishing

Releases are published to [PyPI](https://pypi.org/project/gitlab-mr-commenter/)
automatically when a version tag is pushed (see `.github/workflows/publish.yml`).
The workflow uses [Trusted Publishing (OIDC)](https://docs.pypi.org/trusted-publishers/)
so no API token needs to be stored in GitHub secrets — set it up once on PyPI's
side under your project's Publishing settings.

```bash
# Bump the version in pyproject.toml, then:
git tag v0.2.0
git push origin v0.2.0
```

To publish manually:

```bash
uv build
uv publish
```

---

## License

MIT
