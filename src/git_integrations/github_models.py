from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from src.models.github_webhook import WebhookPullRequest, WebhookRepository

class PRFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None  # The code diff snippet for this file
    content: Optional[str] = None  # The entire code/content of the file at PR head
    raw_content: Optional[str] = None  # Alias for entire content
    raw_url: Optional[str] = None
    blob_url: Optional[str] = None

class PRCommit(BaseModel):
    sha: str
    message: str
    author: str

class PRComment(BaseModel):
    user: str
    body: str
    created_at: str

class PullRequestContext(BaseModel):
    # Core PR information
    title: str
    description: Optional[str] = None
    pr_number: int
    state: str
    html_url: str
    repo_name: str
    owner: str
    head_branch: str
    head_sha: str
    base_branch: str
    base_sha: str

    # Full files with complete source code & diffs
    files: List[PRFile]
    commits: List[PRCommit] = []
    comments: List[PRComment] = []

    # Original webhook models for full context
    pr_metadata: Optional[WebhookPullRequest] = None
    repo_metadata: Optional[WebhookRepository] = None
