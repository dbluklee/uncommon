from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    source_global_url = Column(Text, nullable=True)  # 영문 사이트 URL
    source_kr_url = Column(Text, nullable=True)  # 한글 사이트 URL
    product_name = Column(Text, nullable=False)  # 제품명
    color = Column(Text, nullable=True)  # 색상
    price = Column(JSONB, default={})  # 가격 JSON: {"global": "", "kr": ""}
    reward_points = Column(JSONB, default={})  # 리워드 포인트 JSON: {"global": "", "kr": ""}
    description = Column(JSONB, default={})  # 제품 설명 JSON: {"global": "", "kr": ""}
    material = Column(JSONB, default={})  # 재질 JSON: {"global": "", "kr": ""}
    size = Column(JSONB, default={})  # 사이즈 JSON: {"global": "", "kr": ""}
    issoldout = Column(Boolean, default=False, name='issoldout')  # 품절 여부
    indexed = Column(Boolean, default=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship with images
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_data = Column(LargeBinary, nullable=False)  # 이미지 바이너리 데이터
    image_order = Column(Integer, default=0)  # 이미지 순서
    
    # Relationship with product
    product = relationship("Product", back_populates="images")

class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    target_url = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    products_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)