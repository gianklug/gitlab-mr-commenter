#!/usr/bin/env python3
"""Example: call gitlab-mr-commenter from a Python script.

Run (env vars must be set, see README):

    python examples/python-script.py
"""

import os
import subprocess
from gitlab_mr_commenter import MRCommenter

output = subprocess.check_output(["date", "-u"], text=True).strip()

content = f"""\
## Pipeline info

Triggered at {output} by job [{os.environ.get('CI_JOB_ID', 'local')}]({os.environ.get('CI_JOB_URL', '')})."""

commenter = MRCommenter()  # token + api_url from env
commenter.post(
    project_id=int(os.environ["CI_PROJECT_ID"]),
    mr_iid=int(os.environ["CI_MERGE_REQUEST_IID"]),
    comment_id="my-comment-slot",
    content=content,
)
