"""
Database Module - إعداد الاتصال بقاعدة البيانات
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config.settings import get_settings

settings = get_settings()

# إنشاء قاعدة البيانات بدون URL في create_engine
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,  # Use NullPool for async compatibility
    **settings.database_settings
)

# إنشاء Session Maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class للنماذج
Base = declarative_base()


def get_db():
    """الحصول على جلسة قاعدة البيانات"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """تهيئة قاعدة البيانات - إنشاء جميع الجداول"""
    Base.metadata.create_all(bind=engine)
