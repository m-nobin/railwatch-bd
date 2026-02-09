# github.py - GitHub webhook endpoint

from fastapi import Request, HTTPException, status
from fastapi.responses import PlainTextResponse
import hmac
import hashlib
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

# Critical: Validate that GITHUB_SECRET is configured
GITHUB_SECRET = os.getenv("GITHUB_SECRET")
if not GITHUB_SECRET:
    logger.warning("GITHUB_SECRET not configured - webhook signature verification will fail")
    GITHUB_SECRET = ""
GITHUB_SECRET = GITHUB_SECRET.encode()


def verify_github_signature(request_body: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    signature = signature_header.split("=")[1]
    mac = hmac.new(GITHUB_SECRET, msg=request_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, signature)


async def github_webhook(request: Request):
    """Handle GitHub webhook for auto-deployment"""
    signature = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    
    if not verify_github_signature(body, signature):
        logger.warning("GitHub webhook received with invalid signature")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    
    user_agent = request.headers.get("User-Agent", "")
    if not user_agent.startswith("GitHub-Hookshot/"):
        logger.warning(f"GitHub webhook received with invalid User-Agent: {user_agent}")
        raise HTTPException(status_code=403, detail="Invalid User-Agent")
    
    payload = await request.json()
    logger.info(f"Received valid GitHub webhook: {payload.get('ref', 'unknown')}")
    
    # Security: Use array form instead of shell=True to prevent command injection
    try:
        subprocess.Popen(["bash", "restart_app.sh"], 
                        stdout=open('restart.log', 'a'),
                        stderr=subprocess.STDOUT,
                        start_new_session=True)
        logger.info("Restart script triggered successfully")
    except Exception as e:
        logger.error(f"Failed to trigger restart script: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger restart")
    
    return PlainTextResponse("Pulled and restarted", status_code=200)
