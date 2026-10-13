from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class WebhookUser(BaseModel):
    login: str

class WebhookBranch(BaseModel):
    ref: str
    sha: str

class WebhookLinksStatuses(BaseModel):
    href: str

class WebhookLinks(BaseModel):
    statuses: WebhookLinksStatuses

class WebhookRepository(BaseModel):
    full_name: str
    owner: WebhookUser
    language: Optional[str] = None
    default_branch: Optional[str] = None

class WebhookPullRequest(BaseModel):
    # === PR BASICS ===
    title: str
    body: Optional[str] = None
    number: int
    state: str
    html_url: str
    draft: bool = False
    merged: bool = False
    created_at: str
    updated_at: str
    url: str

    # === CODE DIFFS ===
    diff_url: str
    patch_url: str

    # === FILES CHANGED ===
    changed_files: int
    additions: int
    deletions: int

    # === COMMENTS ===
    comments: int
    review_comments: int
    comments_url: str
    review_comments_url: str

    # === COMMITS ===
    commits: int
    commits_url: str

    # === BRANCHES / SHAS ===
    head: WebhookBranch
    base: WebhookBranch

    # === AUTHOR ===
    user: WebhookUser
    author_association: str

    # === REVIEW METADATA ===
    requested_reviewers: List[WebhookUser] = []
    assignees: List[WebhookUser] = []
    labels: List[Dict[str, Any]] = []
    milestone: Optional[Dict[str, Any]] = None

    # === MERGE / CI STATUS ===
    mergeable: Optional[bool] = None
    mergeable_state: str
    links: WebhookLinks = Field(alias="_links")

class PullRequestWebhookPayload(BaseModel):
    action: str
    number: int
    pull_request: WebhookPullRequest
    repository: WebhookRepository
    sender: WebhookUser
