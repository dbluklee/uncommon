import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, LargeBinary, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env.global')
load_dotenv()

# Database configuration - 환경변수 필수 (기본값 없음, 에러 발생)
POSTGRES_USER = os.environ['POSTGRES_USER']
POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD'] 
POSTGRES_HOST = os.environ['POSTGRES_HOST']
POSTGRES_DB = os.environ['POSTGRES_DB']
# 컨테이너 간 통신에서는 내부 포트 사용
POSTGRES_INTERNAL_PORT = os.environ['POSTGRES_INTERNAL_PORT']

print(f"🔗 데이터베이스 연결 정보: {POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_INTERNAL_PORT}/{POSTGRES_DB}")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_INTERNAL_PORT}/{POSTGRES_DB}"

# Create engine and session
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models - 실제 PostgreSQL 스키마에 맞춤
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    source_global_url = Column(Text)
    source_kr_url = Column(Text)
    product_name = Column(Text, nullable=False)
    color = Column(Text)
    price = Column(JSONB, default='{}')
    reward_points = Column(JSONB, default='{}')
    description = Column(JSONB, default='{}')
    material = Column(JSONB, default='{}')
    size = Column(JSONB, default='{}')
    issoldout = Column(Boolean, default=False)
    indexed = Column(Boolean, default=False)
    scraped_at = Column(DateTime, server_default=func.now())
    indexed_at = Column(DateTime)
    
    # Relationship
    images = relationship("ProductImage", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    image_data = Column(LargeBinary, nullable=False)
    image_order = Column(Integer, default=0)
    
    # Relationship
    product = relationship("Product", back_populates="images")

class IndexingJob(Base):
    __tablename__ = "indexing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    products_total = Column(Integer, default=0)
    products_indexed = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")

if __name__ == "__main__":
    init_db()