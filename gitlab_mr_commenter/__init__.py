"""gitlab-mr-commenter: post and idempotently update comments on GitLab MRs.

Each comment slot is identified by a hidden HTML marker embedded at the end
of the comment body.  Re-running with the same ``comment_id`` updates the
existing comment rather than creating a duplicate.

Typical CI usage
----------------
The following environment variables are read automatically when the
corresponding keyword argument is omitted:

* ``GITLAB_MR_PLAN_TOKEN`` (preferred) or ``GITLAB_TOKEN`` — API token
* ``CI_API_V4_URL`` — GitLab API base URL
* ``CI_PROJECT_ID`` — project ID
* ``CI_MERGE_REQUEST_IID`` — MR internal ID (project-scoped, visible in URLs)

Quick start
-----------
As a library::

    from gitlab_mr_commenter import MRCommenter

    commenter = MRCommenter()          # reads token + URL from env
    commenter.post("## Plan\\n\\nNo changes.")  # project_id/mr_iid from env

    # or explicitly:
    commenter.post(
        content="## Plan\\n\\nNo changes.",
        project_id=123,
        mr_iid=45,
        comment_id="plan-production",
    )

    # local fallback: prints to stdout when CI_API_V4_URL is not set
    commenter = MRCommenter(local_fallback=True)
    commenter.post("## Plan\\n\\nNo changes.")

As a one-shot function::

    from gitlab_mr_commenter import post_comment

    post_comment("## Plan\\n\\nNo changes.")  # all from env
    post_comment("## Plan\\n\\nNo changes.", project_id=123, mr_iid=45, comment_id="plan-production")

From the command line::

    echo "## Plan" | gitlab-mr-commenter plan-production
    echo "## Plan" | gitlab-mr-commenter --project-id 123 --mr-iid 45 plan-production
"""

from __future__ import annotations

import json
import os
from typing import Optional

import gitlab

__all__ = ["COMMENT_IDENTIFIER", "MRCommenter", "post_comment"]

# Hidden HTML marker embedded at the end of every managed comment.
# Matches the Go reference: `<!-- gitlab-mr-commenter id=%q -->` (%q → JSON string).
COMMENT_IDENTIFIER = "<!-- gitlab-mr-commenter id={} -->"


def _marker(comment_id: str) -> str:
    """Return the full hidden marker for *comment_id*.

    Uses ``json.dumps`` to produce a double-quoted, escaped string — the same
    output as Go's ``%q`` verb for plain ASCII identifiers.
    """
    return COMMENT_IDENTIFIER.format(json.dumps(comment_id))


class MRCommenter:
    """Post and idempotently update comments on a GitLab merge request.

    Parameters
    ----------
    token:
        GitLab personal / project / CI access token.  Falls back to the
        ``GITLAB_MR_PLAN_TOKEN`` or ``GITLAB_TOKEN`` environment
        variables.
    api_url:
        GitLab API v4 base URL (e.g. ``https://gitlab.com/api/v4``).  Falls
        back to ``CI_API_V4_URL``.
    local_fallback:
        When ``True`` and no API URL is available, :meth:`post` prints the
        comment body to stdout instead of raising an error.  Useful for
        running scripts locally without GitLab CI environment variables set.
        Defaults to ``False``.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        api_url: Optional[str] = None,
        local_fallback: bool = False,
    ) -> None:
        resolved_url = api_url or os.environ.get("CI_API_V4_URL")

        if not resolved_url:
            if not local_fallback:
                raise ValueError(
                    "No GitLab API URL found. Pass api_url= or set CI_API_V4_URL."
                )
            self._gl = None
            return

        resolved_token = (
            token
            or os.environ.get("GITLAB_MR_PLAN_TOKEN")
            or os.environ.get("GITLAB_TOKEN")
        )
        if not resolved_token:
            raise ValueError(
                "No GitLab token found. Pass token= or set "
                "GITLAB_MR_PLAN_TOKEN / GITLAB_TOKEN."
            )

        instance_url = resolved_url.removesuffix("/api/v4")
        self._gl = gitlab.Gitlab(instance_url, private_token=resolved_token)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def post(
        self,
        content: str,
        project_id: Optional[int] = None,
        mr_iid: Optional[int] = None,
        comment_id: str = "gitlab-mr-commenter",
    ) -> None:
        """Post or update a comment on a merge request.

        If a note whose body contains the hidden marker for *comment_id*
        already exists, it is updated in place.  Otherwise a new note is
        created.

        When the instance was created with ``local_fallback=True`` and no API
        URL was available, the comment body is printed to stdout instead.

        Parameters
        ----------
        content:
            Markdown body of the comment (without the trailing marker — that
            is appended automatically).
        project_id:
            Numeric GitLab project ID. Falls back to ``$CI_PROJECT_ID``.
        mr_iid:
            Merge request **internal** ID — the project-scoped number shown
            in the URL. Falls back to ``$CI_MERGE_REQUEST_IID``.
        comment_id:
            Opaque string that uniquely names this comment slot. Two calls
            with the same *comment_id* on the same MR update the same note.
            Defaults to ``"gitlab-mr-commenter"``.
        """
        if self._gl is None:
            for line in content.splitlines():
                print("== Merge request output: ==")
                print(f"## {line}")
            return

        if project_id is None:
            raw = os.environ.get("CI_PROJECT_ID", "")
            if not raw:
                raise ValueError(
                    "project_id not provided and CI_PROJECT_ID is not set."
                )
            project_id = int(raw)

        if mr_iid is None:
            raw = os.environ.get("CI_MERGE_REQUEST_IID", "")
            if not raw:
                raise ValueError(
                    "mr_iid not provided and CI_MERGE_REQUEST_IID is not set."
                )
            mr_iid = int(raw)

        marker = _marker(comment_id)
        body = f"{content}\n\n{marker}"

        project = self._gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)

        # Walk all pages lazily; stop as soon as we find a matching note.
        for note in mr.notes.list(as_list=False):
            if marker in note.body:
                note.body = body
                note.save()
                return

        # No existing comment — create one.
        mr.notes.create({"body": body})


def post_comment(
    content: str,
    project_id: Optional[int] = None,
    mr_iid: Optional[int] = None,
    comment_id: str = "gitlab-mr-commenter",
    *,
    token: Optional[str] = None,
    api_url: Optional[str] = None,
    local_fallback: bool = False,
) -> None:
    """Convenience wrapper around :class:`MRCommenter`.

    All parameters mirror :meth:`MRCommenter.post`; *token*, *api_url*, and
    *local_fallback* fall back to the same behaviour as the constructor.
    """
    MRCommenter(token=token, api_url=api_url, local_fallback=local_fallback).post(
        content, project_id, mr_iid, comment_id
    )
