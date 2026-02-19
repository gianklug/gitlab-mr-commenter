"""CLI entry point for gitlab-mr-commenter.

Usage
-----
Minimal — all values from CI environment variables::

    echo "## Plan" | gitlab-mr-commenter

With an explicit comment slot name::

    echo "## Plan" | gitlab-mr-commenter plan-production

Fully explicit::

    echo "## Plan" | gitlab-mr-commenter \\
        --project-id 123 \\
        --mr-iid 45 \\
        --token "$GITLAB_TOKEN" \\
        --api-url "https://gitlab.com/api/v4" \\
        plan-production

Also callable as a module::

    echo "## Plan" | python -m gitlab_mr_commenter
"""

from __future__ import annotations

import argparse
import sys

from . import MRCommenter


DEFAULT_COMMENT_ID = "gitlab-mr-commenter"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="gitlab-mr-commenter",
        description=(
            "Post or update a GitLab MR comment identified by COMMENT_ID. "
            "Content is read from stdin. Re-running with the same COMMENT_ID "
            "updates the existing comment in place."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "environment variables (used when flags are omitted):\n"
            "  CI_PROJECT_ID              GitLab project ID\n"
            "  CI_MERGE_REQUEST_IID       MR internal ID\n"
            "  CI_API_V4_URL              GitLab API base URL\n"
            "  GITLAB_MR_PLAN_TOKEN  API token (preferred)\n"
            "  GITLAB_TOKEN          API token (deprecated fallback)\n"
        ),
    )

    parser.add_argument(
        "comment_id",
        metavar="COMMENT_ID",
        nargs="?",
        default=DEFAULT_COMMENT_ID,
        help=(
            f"Unique name for this comment slot (default: '{DEFAULT_COMMENT_ID}'). "
            "A second run with the same value updates the existing comment."
        ),
    )
    parser.add_argument(
        "--project-id",
        type=int,
        default=None,
        metavar="ID",
        help="GitLab project ID. Defaults to $CI_PROJECT_ID.",
    )
    parser.add_argument(
        "--mr-iid",
        type=int,
        default=None,
        metavar="IID",
        help="Merge request internal ID. Defaults to $CI_MERGE_REQUEST_IID.",
    )
    parser.add_argument(
        "--token",
        default=None,
        metavar="TOKEN",
        help=(
            "GitLab API token. Defaults to $GITLAB_MR_PLAN_TOKEN " "or $GITLAB_TOKEN."
        ),
    )
    parser.add_argument(
        "--api-url",
        default=None,
        metavar="URL",
        help="GitLab API base URL. Defaults to $CI_API_V4_URL.",
    )

    args = parser.parse_args(argv)

    content = sys.stdin.read()
    if not content.strip():
        parser.error("stdin is empty — nothing to post.")

    try:
        MRCommenter(token=args.token, api_url=args.api_url).post(
            content=content,
            project_id=args.project_id,
            mr_iid=args.mr_iid,
            comment_id=args.comment_id,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
