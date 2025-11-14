from sqlalchemy import text
from .db import engine
from .db import Base  # ensures metadata is available
from . import models  # noqa: F401 ensure models are imported for metadata


def main():
    # 打印脱敏后的连接信息
    try:
        safe_url = engine.url.set(password="***")
        print(f"[init-db] Using DB: {safe_url}")
    except Exception:
        print("[init-db] Using DB engine (url hidden)")

    # 探活连接
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("[init-db] Connection OK")

    # 创建所有表（幂等）
    Base.metadata.create_all(bind=engine)
    print("[init-db] create_all done. Tables:")
    for name in sorted(Base.metadata.tables.keys()):
        print(" -", name)


if __name__ == "__main__":
    main()