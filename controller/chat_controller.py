import os
import json
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

# Import from controller/server packages; keep runtime-safe
try:
    from controller.llm_client import VolcClient, build_empathy_system_prompt  # type: ignore
    from server.models import Conversation  # type: ignore
except Exception:
    # Fallback to path-based import
    import importlib.util
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def _load(abs_rel_path: str, name: str):
        path = os.path.join(ROOT, abs_rel_path)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f'Cannot load {abs_rel_path}')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod
    _llm = _load(os.path.join('controller', 'llm_client.py'), 'local_ctrl_llm')
    _models = _load(os.path.join('server', 'models.py'), 'local_server_models')
    VolcClient = _llm.VolcClient
    build_empathy_system_prompt = _llm.build_empathy_system_prompt
    Conversation = _models.Conversation


def _write_control_artifact(session_id: Optional[str], user_text: str, reply_text: str, created_at: str) -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, 'control')
    os.makedirs(out_dir, exist_ok=True)
    fname = f"{created_at.replace(':','-').replace('.','-')}_{(session_id or 'nosession')[:12]}.json"
    payload = {
        'sessionId': session_id,
        'createdAt': created_at,
        'input': user_text,
        'reply': reply_text,
    }
    with open(os.path.join(out_dir, fname), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def do_chat(db: Session, text: str, history: Optional[List[Dict[str, str]]], session_id: Optional[str]):
    system_prompt = build_empathy_system_prompt()
    messages: List[Dict[str, str]] = [{'role': 'system', 'content': system_prompt}]
    if history:
        for m in history[-10:]:
            role = m.get('role') or 'user'
            content = m.get('content') or ''
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': text})

    client = VolcClient()
    reply = client.chat(messages)
    created_at = datetime.utcnow().isoformat()

    # persist to DB
    db.add(Conversation(session_id=session_id or None, role='user', content=text))
    db.add(Conversation(session_id=session_id or None, role='assistant', content=reply))
    db.commit()

    # control artifact
    _write_control_artifact(session_id or None, text, reply, created_at)
    return reply, created_at


def query_conversations(db: Session, session_id: Optional[str], page: int, page_size: int, order: Literal['asc','desc']):
    q = db.query(Conversation)
    if session_id is not None:
        q = q.filter(Conversation.session_id == session_id)
    total = q.count()
    sorter = asc if order == 'asc' else desc
    items = (q.order_by(sorter(Conversation.created_at))
               .offset((page-1)*page_size)
               .limit(page_size)
               .all())
    def to_dict(m):
        return {
            'id': m.id,
            'sessionId': m.session_id,
            'role': m.role,
            'content': m.content,
            'createdAt': m.created_at.isoformat(),
        }
    return {
        'items': [to_dict(i) for i in items],
        'page': page,
        'pageSize': page_size,
        'total': total,
    }


def query_sessions(db: Session, page: int, page_size: int):
    q = (db.query(
            Conversation.session_id.label('sid'),
            func.count(Conversation.id).label('cnt'),
            func.min(Conversation.created_at).label('first_at'),
            func.max(Conversation.created_at).label('last_at'),
        )
        .group_by(Conversation.session_id)
        .order_by(desc(func.max(Conversation.created_at))))
    total = q.count()
    rows = q.offset((page-1)*page_size).limit(page_size).all()
    items = []
    now_iso = datetime.utcnow().isoformat()
    for r in rows:
        items.append({
            'sessionId': r.sid,
            'count': int(r.cnt or 0),
            'firstAt': (r.first_at.isoformat() if r.first_at else now_iso),
            'lastAt': (r.last_at.isoformat() if r.last_at else now_iso),
        })
    return {
        'items': items,
        'page': page,
        'pageSize': page_size,
        'total': total,
    }