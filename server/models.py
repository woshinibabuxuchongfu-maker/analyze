from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.mysql import LONGTEXT

try:
    from .db import Base  # type: ignore
except Exception:
    import os
    import importlib.util

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(ROOT, 'server', 'db.py')
    spec_db = importlib.util.spec_from_file_location('local_server_db', db_path)
    if spec_db is None or spec_db.loader is None:
        raise RuntimeError('Cannot load server/db.py for models')
    _db = importlib.util.module_from_spec(spec_db)
    spec_db.loader.exec_module(_db)  # type: ignore
    Base = _db.Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # 'user' | 'assistant'
    content = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class FootballAnalysis(Base):
    __tablename__ = "football_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=True)
    result_json = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class BasketballAnalysis(Base):
    __tablename__ = "basketball_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=True)
    result_json = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)