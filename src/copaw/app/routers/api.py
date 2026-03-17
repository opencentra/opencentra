# -*- coding: utf-8 -*-
"""External API routes for third-party integration."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from copaw.config import load_config

router = APIRouter(prefix="/external", tags=["external"])


class FeishuSendMessage(BaseModel):
    """Request body for sending message to Feishu."""

    message: str = Field(..., description="Message content to send")


@router.post(
    "/feishu/send",
    summary="Send message to Feishu",
    description="Send a text message to the pre-configured Feishu recipient",
)
async def feishu_send(
    request: Request,
    body: FeishuSendMessage,
) -> dict:
    """Send a text message to Feishu using pre-configured recipient."""
    config = load_config()
    feishu_config = config.channels.feishu

    if not feishu_config.enabled:
        raise HTTPException(
            status_code=400,
            detail="Feishu channel is not enabled",
        )

    if not feishu_config.app_id or not feishu_config.app_secret:
        raise HTTPException(
            status_code=400,
            detail="Feishu app_id and app_secret are required",
        )

    if not feishu_config.notify_receive_id:
        raise HTTPException(
            status_code=400,
            detail="Feishu notify_receive_id is not configured",
        )

    channel_manager = getattr(request.app.state, "channel_manager", None)
    if channel_manager is None:
        raise HTTPException(
            status_code=500,
            detail="Channel manager not initialized",
        )

    try:
        await channel_manager.send_text(
            channel="feishu",
            user_id=feishu_config.notify_receive_id,
            session_id="",
            text=body.message,
            meta={
                "feishu_receive_id": feishu_config.notify_receive_id,
                "feishu_receive_id_type": feishu_config.notify_receive_id_type,
            },
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}",
        )
