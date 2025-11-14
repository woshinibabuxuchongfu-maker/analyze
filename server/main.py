from fastapi import FastAPI, Depends, Query, Path, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
from sqlalchemy.orm import Session
import os
import importlib.util

try:
    from .db import engine, get_db  # type: ignore
    from .models import Base  # ensure metadata is populated
    from controller.chat_controller import do_chat, query_conversations, query_sessions  # type: ignore
    from controller.analysis_controller import analyze_game, list_results, get_result  # type: ignore
    from controller.search_controller import search_and_analyze  # type: ignore
except Exception:
    # Fallback when executed outside package context (e.g., dynamic loader)
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    def _load_mod(rel_path: str, name: str):
        path = os.path.join(ROOT, 'server', rel_path)
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f'Cannot load {rel_path}')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return mod
    _db = _load_mod('db.py', 'local_server_db')
    _models = _load_mod('models.py', 'local_server_models')
    engine = _db.engine
    get_db = _db.get_db
    Base = _models.Base
    # load controller/chat_controller dynamically
    import importlib.util as _ilu
    ctrl_path = os.path.join(ROOT, 'controller', 'chat_controller.py')
    spec_ctrl = _ilu.spec_from_file_location('local_chat_ctrl', ctrl_path)
    if spec_ctrl is None or spec_ctrl.loader is None:
        raise RuntimeError('Cannot load controller/chat_controller.py')
    _ctrl = _ilu.module_from_spec(spec_ctrl)
    spec_ctrl.loader.exec_module(_ctrl)  # type: ignore
    do_chat = _ctrl.do_chat
    query_conversations = _ctrl.query_conversations
    query_sessions = _ctrl.query_sessions

    # load controller/analysis_controller dynamically
    ana_path = os.path.join(ROOT, 'controller', 'analysis_controller.py')
    spec_ana = _ilu.spec_from_file_location('local_analysis_ctrl', ana_path)
    if spec_ana is None or spec_ana.loader is None:
        raise RuntimeError('Cannot load controller/analysis_controller.py')
    _ana = _ilu.module_from_spec(spec_ana)
    spec_ana.loader.exec_module(_ana)  # type: ignore
    analyze_game = _ana.analyze_game
    list_results = _ana.list_results
    get_result = _ana.get_result

    sch_path = os.path.join(ROOT, 'controller', 'search_controller.py')
    spec_sch = _ilu.spec_from_file_location('local_search_ctrl', sch_path)
    if spec_sch is None or spec_sch.loader is None:
        raise RuntimeError('Cannot load controller/search_controller.py')
    _sch = _ilu.module_from_spec(spec_sch)
    spec_sch.loader.exec_module(_sch)  # type: ignore
    search_and_analyze = _sch.search_and_analyze


def create_app() -> FastAPI:
    app = FastAPI(title="Analyze Service")

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    # --- Static Web (serve / and /assets) ---
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    WEB_DIR = os.path.join(ROOT, 'web')
    ASSETS_DIR = os.path.join(WEB_DIR, 'assets')
    if os.path.isdir(ASSETS_DIR):
        app.mount('/assets', StaticFiles(directory=ASSETS_DIR), name='assets')

    @app.get('/')
    def index_html():
        index_path = os.path.join(WEB_DIR, 'index.html')
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"ok": True, "hint": "index.html not found. Ensure web/ exists."}

    @app.get('/{page}.html')
    def static_page(page: str):
        # 简单防穿越处理
        if '..' in page or '/' in page or '\\' in page:
            raise HTTPException(status_code=400, detail='invalid page')
        file_path = os.path.join(WEB_DIR, f'{page}.html')
        if os.path.exists(file_path):
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail='page not found')

    # --- Chat API ---
    class ChatMessage(BaseModel):
        role: Literal['user', 'assistant']
        content: str

    class ChatRequest(BaseModel):
        text: str
        history: Optional[List[ChatMessage]] = None
        sessionId: Optional[str] = None

    class ChatResponse(BaseModel):
        reply: str
        createdAt: str

    @app.post('/api/chat', response_model=ChatResponse)
    def api_chat(body: ChatRequest, db: Session = Depends(get_db)):
        history_payload = [m.dict() for m in body.history] if body.history else None
        reply, created_at = do_chat(db, body.text, history_payload, body.sessionId)
        return ChatResponse(reply=reply, createdAt=created_at)

    # --- Conversations timeline ---
    @app.get('/api/conversations')
    def api_conversations(sessionId: Optional[str] = Query(default=None),
                          page: int = Query(default=1, ge=1),
                          pageSize: int = Query(default=20, ge=1, le=100),
                          order: Literal['asc','desc'] = Query(default='desc'),
                          db: Session = Depends(get_db)):
        return query_conversations(db, sessionId, page, pageSize, order)

    @app.get('/api/conversation-sessions')
    def api_conversation_sessions(page: int = Query(default=1, ge=1),
                                  pageSize: int = Query(default=20, ge=1, le=100),
                                  db: Session = Depends(get_db)):
        return query_sessions(db, page, pageSize)

    # --- Analyze APIs ---
    class AnalyzeBody(BaseModel):
        sport: Literal['football','basketball']
        modelId: Optional[str] = None
        temperature: Optional[float] = None
        dataText: str

    @app.post('/api/analyze')
    def api_analyze(body: AnalyzeBody, db: Session = Depends(get_db)):
        return analyze_game(db, body.sport, body.dataText, body.modelId, body.temperature)

    @app.get('/api/results')
    def api_results(sport: Optional[Literal['football','basketball']] = Query(default=None),
                    db: Session = Depends(get_db)):
        return list_results(db, sport)

    @app.get('/api/results/{rid}')
    def api_get_result(rid: int = Path(..., ge=1), db: Session = Depends(get_db)):
        data = get_result(db, rid)
        if data is None:
            return {"error": "not_found"}
        return data

    class SearchRequest(BaseModel):
        query: str
        temperature: Optional[float] = None

    class SearchResponse(BaseModel):
        ok: bool
        query: str
        createdAt: str
        summary: str
        hits: List[dict]

    @app.post('/api/search', response_model=SearchResponse)
    def api_search(body: SearchRequest):
        data = search_and_analyze(body.query, body.temperature)
        return SearchResponse(**data)

    return app


app = create_app()