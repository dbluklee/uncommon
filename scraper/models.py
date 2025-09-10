# RAG LLM 시스템의 데이터베이스 모델 정의 파일
# 목적: PostgreSQL 데이터베이스의 테이블 구조를 SQLAlchemy ORM으로 정의
# 관련 파일: database.py (Base 클래스), main.py (모델 사용)
# 테이블: products (제품), product_images (제품 이미지), scraping_jobs (스크래핑 작업)

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB  # PostgreSQL JSONB 타입 - JSON 데이터 효율적 저장
from sqlalchemy.sql import func  # 데이터베이스 함수 (NOW() 등)
from sqlalchemy.orm import relationship  # 테이블 간 관계 정의
from database import Base  # SQLAlchemy Base 클래스

# 제품 정보 테이블 모델 - UNCOMMON 안경 제품의 모든 속성을 저장
# 목적: 영문/한글 사이트에서 수집된 제품 데이터의 통합 저장소 역할
# 관련 함수: ProductScraper.scrape_products_both_sites (scraper.py)
# 특징: JSONB 컬럼으로 다국어 데이터 효율적 저장, 벡터 인덱싱 상태 추적
class Product(Base):
    __tablename__ = "products"
    
    # 기본 식별자 및 소스 URL
    id = Column(Integer, primary_key=True, index=True)  # 제품 고유 ID
    source_global_url = Column(Text, nullable=True)  # 영문 사이트 제품 페이지 URL
    source_kr_url = Column(Text, nullable=True)  # 한글 사이트 제품 페이지 URL
    
    # 제품 기본 정보
    product_name = Column(Text, nullable=False)  # 제품명 (필수)
    color = Column(Text, nullable=True)  # 색상 정보
    
    # JSONB로 저장되는 다국어 데이터 - {"global": "영문값", "kr": "한글값"} 형태
    price = Column(JSONB, default={})  # 가격 정보
    reward_points = Column(JSONB, default={})  # 리워드 포인트
    description = Column(JSONB, default={})  # 상세 설명
    material = Column(JSONB, default={})  # 재질/소재 정보
    size = Column(JSONB, default={})  # 사이즈 정보
    
    # 상태 관리 필드
    issoldout = Column(Boolean, default=False, name='issoldout')  # 품절 여부
    indexed = Column(Boolean, default=False)  # 벡터 DB 인덱싱 완료 여부
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())  # 스크래핑 시점
    indexed_at = Column(DateTime(timezone=True), nullable=True)  # 인덱싱 완료 시점
    
    # 관계 정의: 제품 1개 - 이미지 N개 (One-to-Many)
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

# 제품 이미지 테이블 모델 - 제품별 이미지를 바이너리로 저장
# 목적: 제품 이미지를 PostgreSQL BYTEA 형태로 직접 저장하여 외부 의존성 제거
# 관련 함수: ProductScraper.save_image (scraper.py), 멀티모달 검색 기능
# 특징: CASCADE 삭제로 제품 삭제 시 이미지도 함께 삭제, 순서 관리
class ProductImage(Base):
    __tablename__ = "product_images"
    
    id = Column(Integer, primary_key=True, index=True)  # 이미지 고유 ID
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)  # 제품 외래키
    image_data = Column(LargeBinary, nullable=False)  # 이미지 바이너리 데이터 (BYTEA)
    image_order = Column(Integer, default=0)  # 이미지 표시 순서 (0부터 시작)
    
    # 관계 정의: 이미지 N개 - 제품 1개 (Many-to-One)
    product = relationship("Product", back_populates="images")

# 스크래핑 작업 추적 테이블 모델 - 웹 스크래핑 작업의 상태와 결과를 기록
# 목적: 스크래핑 작업의 생명주기 관리 및 중복 실행 방지
# 관련 함수: start_scraping, run_scraping (main.py)
# 상태: pending → running → completed/failed 순서로 진행
class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"
    
    id = Column(Integer, primary_key=True, index=True)  # 작업 고유 ID
    target_url = Column(Text, nullable=False)  # 스크래핑 대상 URL
    status = Column(String(20), default="pending")  # 작업 상태: pending, running, completed, failed
    products_count = Column(Integer, default=0)  # 수집된 제품 수
    started_at = Column(DateTime(timezone=True), server_default=func.now())  # 작업 시작 시간
    completed_at = Column(DateTime(timezone=True), nullable=True)  # 작업 완료 시간