import asyncio
import base64
import httpx
from typing import List, Dict, Any, Optional
from src.git_integrations.github_models import PRFile, PRCommit, PRComment, PullRequestContext
from src.models.github_webhook import WebhookPullRequest, WebhookRepository
from src.config import settings

class GithubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or (settings.github_token.get_secret_value() if hasattr(settings, "github_token") and settings.github_token else None)
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    async def _get(self, client: httpx.AsyncClient, url: str) -> Any:
        response = await client.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    async def _get_file_content(
        self,
        client: httpx.AsyncClient,
        file_item: Dict[str, Any],
        head_sha: str,
        repo_full_name: str
    ) -> Optional[str]:
        """
        Retrieves the entire code of an affected file at the PR's head commit.
        Handles deleted files, raw text decoding, and base64 fallbacks.
        """
        if file_item.get("status") == "removed":
            return None

        # 1. Prefer contents_url which points to the exact file version at PR head
        contents_url = file_item.get("contents_url")
        if not contents_url:
            filename = file_item.get("filename", "")
            contents_url = f"https://api.github.com/repos/{repo_full_name}/contents/{filename}?ref={head_sha}"

        raw_headers = {
            **self.headers,
            "Accept": "application/vnd.github.raw+json"
        }

        try:
            response = await client.get(contents_url, headers=raw_headers)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and data.get("encoding") == "base64" and "content" in data:
                            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                return response.text
        except Exception as e:
            print(f"⚠️ Failed to fetch file content via contents_url for {file_item.get('filename')}: {e}")

        # 2. Fallback to raw_url if available
        raw_url = file_item.get("raw_url")
        if raw_url:
            try:
                response = await client.get(raw_url, headers=self.headers)
                if response.status_code == 200:
                    return response.text
            except Exception as e:
                print(f"⚠️ Failed to fetch file content via raw_url for {file_item.get('filename')}: {e}")

        return None

    async def get_pr_context(self, pr: WebhookPullRequest, repo: WebhookRepository) -> PullRequestContext:
        """
        Builds the complete PR context including:
        - PR title, description, branch, commit, and repo metadata
        - All affected files with both patch diffs AND their entire source code
        - Commit list and comments
        """
        async with httpx.AsyncClient() as client:
            # 1. Fetch changed files metadata
            files_data = await self._get(client, f"{pr.url}/files")

            async def process_file(f: Dict[str, Any]) -> PRFile:
                full_code = await self._get_file_content(
                    client=client,
                    file_item=f,
                    head_sha=pr.head.sha,
                    repo_full_name=repo.full_name
                )
                return PRFile(
                    filename=f["filename"],
                    status=f["status"],
                    additions=f["additions"],
                    deletions=f["deletions"],
                    changes=f["changes"],
                    patch=f.get("patch"),
                    content=full_code,
                    raw_content=full_code,
                    raw_url=f.get("raw_url"),
                    blob_url=f.get("blob_url")
                )

            # Concurrently fetch entire code for all affected files
            files_task = asyncio.gather(*(process_file(f) for f in files_data))

            # 2. Concurrently fetch commits and comments
            commits_task = self._get(client, pr.commits_url)
            issue_comments_task = self._get(client, pr.comments_url)
            review_comments_task = self._get(client, pr.review_comments_url)

            files, commits_data, issue_comments, review_comments = await asyncio.gather(
                files_task,
                commits_task,
                issue_comments_task,
                review_comments_task
            )

            commits = [
                PRCommit(
                    sha=c["sha"],
                    message=c["commit"]["message"],
                    author=c["commit"]["author"]["name"]
                ) for c in commits_data
            ]

            all_comments = issue_comments + review_comments
            comments = [
                PRComment(
                    user=c["user"]["login"],
                    body=c["body"],
                    created_at=c["created_at"]
                ) for c in all_comments
            ]

            # 3. Assemble complete context
            return PullRequestContext(
                title=pr.title,
                description=pr.body,
                pr_number=pr.number,
                state=pr.state,
                html_url=pr.html_url,
                repo_name=repo.full_name,
                owner=repo.owner.login,
                head_branch=pr.head.ref,
                head_sha=pr.head.sha,
                base_branch=pr.base.ref,
                base_sha=pr.base.sha,
                files=list(files),
                commits=commits,
                comments=comments,
                pr_metadata=pr,
                repo_metadata=repo
            )
