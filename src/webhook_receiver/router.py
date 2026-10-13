from fastapi import APIRouter, Header, Request, HTTPException, Depends
import hmac
import hashlib
from src.config import settings
from src.models.github_webhook import PullRequestWebhookPayload
from src.git_integrations.github_client import GithubClient

router = APIRouter()

async def verify_signature(request: Request, x_hub_signature_256: str = Header(None)):
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    payload = await request.body()
    secret = settings.github_webhook_secret.get_secret_value().encode("utf-8")
    
    expected_signature = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return True

@router.post("/github")
async def github_webhook(
    payload: PullRequestWebhookPayload,
    request: Request, 
    x_github_event: str = Header(None),
    is_valid: bool = Depends(verify_signature)
):
    if x_github_event == "pull_request":
        # GitHub sends 'closed' when a PR is merged or closed. We check the 'merged' flag.
        is_merge = payload.action == "closed" and payload.pull_request.merged
        
        # We only care about opened, synchronize, reopened PRs, or merges
        if payload.action in ["opened", "synchronize", "reopened"] or is_merge:
            pr_data = {
                "action": "merged" if is_merge else payload.action,
                "pr_number": payload.pull_request.number,
                "repo": payload.repository.full_name,
                "owner": payload.repository.owner.login
            }
            
            print(f"✅ Webhook verified! Received PR event: {pr_data}")
            print("🚀 Fetching full PR context (files, diffs, entire code, commits, comments) via API...")
            
            # Fetch the rich PR context via GitHub API
            pr_context = None
            try:
                client = GithubClient()
                pr_context = await client.get_pr_context(
                    pr=payload.pull_request,
                    repo=payload.repository
                )
                print(f"📦 Full Fetched Context:\n{pr_context.model_dump_json(indent=2)}")
            except Exception as e:
                print(f"❌ Error fetching PR context: {e}")
                
            print("🕒 Enqueueing job to ARQ queue... (Queue implementation pending)")
            
            # Future: Push to ARQ queue
            # await request.app.state.redis.enqueue_job('process_pr_review', pr_data)
            
            return {
                "status": "accepted",
                "message": f"PR {pr_data['action']} event queued for processing.",
                "context": pr_context
            }
            
    return {"status": "ignored", "message": f"Event {x_github_event} ignored"}
