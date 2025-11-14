import os
import sys
from sqlalchemy import text
import importlib.util


def main():
    # 确保本地包优先
    ROOT = os.path.dirname(os.path.abspath(__file__))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)

    # 动态按文件路径加载，避免与外部同名包冲突
    server_dir = os.path.join(ROOT, 'server')
    db_path = os.path.join(server_dir, 'db.py')
    models_path = os.path.join(server_dir, 'models.py')

    spec_db = importlib.util.spec_from_file_location('local_server_db', db_path)
    if spec_db is None or spec_db.loader is None:
        raise RuntimeError('Cannot load server/db.py')
    db_mod = importlib.util.module_from_spec(spec_db)
    spec_db.loader.exec_module(db_mod)  # type: ignore

    # 加载 models 以填充 Base.metadata
    spec_models = importlib.util.spec_from_file_location('local_server_models', models_path)
    if spec_models is None or spec_models.loader is None:
        raise RuntimeError('Cannot load server/models.py')
    models_mod = importlib.util.module_from_spec(spec_models)
    spec_models.loader.exec_module(models_mod)  # type: ignore

    engine = db_mod.engine
    # Use Base from models module to ensure it contains all mapped tables
    Base = models_mod.Base

    try:
        safe_url = engine.url.set(password="***")
        print(f"[init-db] Using DB: {safe_url}")
    except Exception:
        print("[init-db] Using DB engine (url hidden)")

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("[init-db] Connection OK")

    Base.metadata.create_all(bind=engine)
    print("[init-db] create_all done. Tables:")
    for name in sorted(Base.metadata.tables.keys()):
        print(" -", name)


if __name__ == "__main__":
    main()