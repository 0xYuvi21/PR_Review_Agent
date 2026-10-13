import asyncio
import json
from src.models.github_webhook import PullRequestWebhookPayload
from src.git_integrations.github_client import GithubClient

SAMPLE_PAYLOAD = {
  "action": "opened",
  "number": 3,
  "pull_request": {
    "url": "https://api.github.com/repos/0xYuvi21/RagMind/pulls/3",
    "id": 4811191818,
    "node_id": "PR_kwDORnd8Ic8AAAABHsT2Cg",
    "html_url": "https://github.com/0xYuvi21/RagMind/pull/3",
    "diff_url": "https://github.com/0xYuvi21/RagMind/pull/3.diff",
    "patch_url": "https://github.com/0xYuvi21/RagMind/pull/3.patch",
    "issue_url": "https://api.github.com/repos/0xYuvi21/RagMind/issues/3",
    "number": 3,
    "state": "open",
    "locked": False,
    "title": "PR Test 3",
    "user": {
      "login": "0xYuvi21"
    },
    "body": None,
    "created_at": "2026-10-10T12:28:31Z",
    "updated_at": "2026-10-10T12:28:31Z",
    "draft": False,
    "commits_url": "https://api.github.com/repos/0xYuvi21/RagMind/pulls/3/commits",
    "review_comments_url": "https://api.github.com/repos/0xYuvi21/RagMind/pulls/3/comments",
    "comments_url": "https://api.github.com/repos/0xYuvi21/RagMind/issues/3/comments",
    "head": {
      "ref": "feature",
      "sha": "67a3d2cb247081394feede74e1bdcf3d63395674"
    },
    "base": {
      "ref": "main",
      "sha": "581234e436c9a2465a4e519b62381e23fb985e24"
    },
    "_links": {
      "statuses": {
        "href": "https://api.github.com/repos/0xYuvi21/RagMind/statuses/67a3d2cb247081394feede74e1bdcf3d63395674"
      }
    },
    "author_association": "OWNER",
    "merged": False,
    "mergeable_state": "unknown",
    "comments": 0,
    "review_comments": 0,
    "commits": 1,
    "additions": 2,
    "deletions": 0,
    "changed_files": 1
  },
  "repository": {
    "full_name": "0xYuvi21/RagMind",
    "owner": {
      "login": "0xYuvi21"
    },
    "language": "Python",
    "default_branch": "main"
  },
  "sender": {
    "login": "0xYuvi21"
  }
}

async def _run_test():
    payload = PullRequestWebhookPayload.model_validate(SAMPLE_PAYLOAD)
    client = GithubClient()
    pr_context = await client.get_pr_context(
        pr=payload.pull_request,
        repo=payload.repository
    )

    print("\n=== RETRIEVED PR CONTEXT ===")
    print(f"Title: {pr_context.title}")
    print(f"Description: {pr_context.description}")
    print(f"PR Number: {pr_context.pr_number}")
    print(f"Repository: {pr_context.repo_name}")
    print(f"Owner: {pr_context.owner}")
    print(f"Head: {pr_context.head_branch} ({pr_context.head_sha})")
    print(f"Total files changed: {len(pr_context.files)}")

    for f in pr_context.files:
        print(f"\n--- File: {f.filename} ({f.status}) ---")
        print(f"Diff Patch:\n{f.patch}")
        print(f"Entire File Code:\n{f.content}")
        assert f.content is not None, f"Expected full file code for {f.filename}"
        assert "Test 3" in f.content, "Expected PR additions in full file content"
        assert "How are you?" in f.content, "Expected base file content preserved in full file code"

    print("\n[SUCCESS] Verification PASSED: Entire file code retrieved successfully!")

def test_full_file_code_retrieval():
    asyncio.run(_run_test())

if __name__ == "__main__":
    test_full_file_code_retrieval()
