import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models.ai_models import AiProviderConfig, AiChatSession, AiChatMessage
from app.core.config import settings
from app.services.ai_service import AiService
from app.log import logger

router = APIRouter()


class FetchModelsRequest(BaseModel):
    api_base_url: str
    api_key: str


class SaveProviderRequest(BaseModel):
    provider_name: str
    api_base_url: str
    api_key: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    message: str


class TestConnectionRequest(BaseModel):
    api_base_url: str
    api_key: str
    model_name: str


def mask_api_key(api_key: str) -> str:
    """脱敏 API Key，只显示前后各 4 位"""
    if len(api_key) <= 8:
        return api_key[:2] + "****" + api_key[-2:]
    return api_key[:4] + "****" + api_key[-4:]


@router.post("/models")
async def fetch_models(req: FetchModelsRequest):
    """获取模型列表"""
    try:
        models = await AiService.fetch_models(req.api_base_url, req.api_key)
        return {"success": True, "data": models}
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取模型列表失败: {str(e)}")


@router.post("/providers")
async def save_provider(req: SaveProviderRequest, db: Session = Depends(get_db)):
    """保存 AI 配置"""
    try:
        # 将之前所有配置设为 inactive
        old_configs = db.query(AiProviderConfig).filter(
            AiProviderConfig.is_active == True
        ).all()
        for config in old_configs:
            config.is_active = False

        # 保存新配置
        new_config = AiProviderConfig(
            provider_name=req.provider_name,
            api_base_url=req.api_base_url,
            api_key=req.api_key,
            model_name=req.model_name,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            system_prompt=req.system_prompt,
            is_active=True
        )
        new_config.create(db)
        db.commit()

        return {"success": True, "message": "配置保存成功"}
    except Exception as e:
        db.rollback()
        logger.error(f"保存 AI 配置失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"保存配置失败: {str(e)}")


@router.get("/providers")
async def get_provider(db: Session = Depends(get_db)):
    """获取当前 AI 配置"""
    config = db.query(AiProviderConfig).filter(
        AiProviderConfig.is_active == True
    ).first()

    if not config:
        return {"success": True, "data": None}

    # 返回时 API Key 脱敏
    config_dict = config.to_dict()
    config_dict["api_key"] = mask_api_key(config.api_key)

    return {"success": True, "data": config_dict}


@router.post("/chat/test")
async def test_connection(req: TestConnectionRequest):
    """测试 AI 连接"""
    try:
        await AiService.test_connection(req.api_base_url, req.api_key, req.model_name)
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        logger.error(f"AI 连接测试失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """AI 对话（SSE 流式）"""
    # 1. 获取/创建 session
    if req.session_id:
        session = db.query(AiChatSession).filter(
            AiChatSession.id == req.session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="对话不存在")
    else:
        # 创建新对话，标题取消息前 30 字
        title = req.message[:30] if len(req.message) > 30 else req.message
        session = AiChatSession(title=title)
        session.create(db)
        db.commit()
        db.refresh(session)

    # 2. 保存用户消息
    user_message = AiChatMessage(
        session_id=session.id,
        role="user",
        content=req.message
    )
    user_message.create(db)
    db.commit()

    # 3. 获取配置
    config = db.query(AiProviderConfig).filter(
        AiProviderConfig.is_active == True
    ).first()
    if not config:
        raise HTTPException(status_code=400, detail="请先配置 AI 服务商")

    # 4. 获取 API_TOKEN
    api_token = settings.API_TOKEN
    if not api_token:
        raise HTTPException(status_code=400, detail="系统 API_TOKEN 未配置")

    # 5. 获取历史消息
    history_messages = db.query(AiChatMessage).filter(
        AiChatMessage.session_id == session.id
    ).order_by(AiChatMessage.created_at.asc()).all()

    history = [
        {"role": m.role, "content": m.content}
        for m in history_messages[:-1]  # 排除刚发送的这条消息
    ]

    provider_config = {
        "model_name": config.model_name,
        "api_base_url": config.api_base_url,
        "api_key": config.api_key,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "system_prompt": config.system_prompt,
    }

    # 6. 流式返回
    async def event_generator():
        full_response = ""
        try:
            async for sse_event in AiService.chat_stream(
                session_id=session.id,
                message=req.message,
                provider_config=provider_config,
                api_token=api_token,
                history_messages=history
            ):
                yield sse_event

                # 收集完整回复，用于保存到数据库
                if sse_event.startswith("event: delta"):
                    # 提取 content
                    data_line = sse_event.split("\n")[1]
                    if data_line.startswith("data: "):
                        data = json.loads(data_line[6:])
                        full_response += data.get("content", "")

                if sse_event.startswith("event: done"):
                    # 保存 AI 回复到数据库
                    try:
                        ai_message = AiChatMessage(
                            session_id=session.id,
                            role="assistant",
                            content=full_response
                        )
                        ai_message.create(db)
                        db.commit()

                        # 更新会话标题（如果还没更新过）
                        current_session = db.query(AiChatSession).filter(
                            AiChatSession.id == session.id
                        ).first()
                        if current_session and current_session.title == req.message[:30]:
                            # 如果标题就是第一条消息，保留
                            pass
                    except Exception as e:
                        logger.error(f"保存 AI 回复失败: {str(e)}")
                        db.rollback()

        except Exception as e:
            logger.error(f"对话流处理出错: {str(e)}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/chat/sessions")
async def list_sessions(db: Session = Depends(get_db)):
    """获取对话历史列表"""
    sessions = db.query(AiChatSession).order_by(
        AiChatSession.updated_at.desc()
    ).all()

    result = []
    for s in sessions:
        session_dict = s.to_dict()
        # 获取消息数量
        message_count = db.query(AiChatMessage).filter(
            AiChatMessage.session_id == s.id
        ).count()
        session_dict["message_count"] = message_count
        result.append(session_dict)

    return {"success": True, "data": result}


@router.get("/chat/sessions/{session_id}/messages")
async def get_messages(session_id: int, db: Session = Depends(get_db)):
    """获取指定对话的消息"""
    session = db.query(AiChatSession).filter(
        AiChatSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = db.query(AiChatMessage).filter(
        AiChatMessage.session_id == session_id
    ).order_by(AiChatMessage.created_at.asc()).all()

    return {
        "success": True,
        "data": {
            "session": session.to_dict(),
            "messages": [m.to_dict() for m in messages]
        }
    }


@router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """删除对话及其所有消息"""
    session = db.query(AiChatSession).filter(
        AiChatSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")

    try:
        session.delete(db, session_id)
        db.commit()
        return {"success": True, "message": "对话已删除"}
    except Exception as e:
        db.rollback()
        logger.error(f"删除对话失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"删除对话失败: {str(e)}")
