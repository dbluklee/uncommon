# RAG LLM 시스템의 PostgreSQL 데이터베이스 연결 및 설정 파일
# 목적: SQLAlchemy를 활용한 데이터베이스 ORM 설정 및 세션 관리
# 관련 파일: models.py (테이블 모델), main.py (세션 사용)
# 의존성: .env.global의 PostgreSQL 환경변수

import os
from sqlalchemy import create_engine  # PostgreSQL 데이터베이스 엔진 생성
from sqlalchemy.ext.declarative import declarative_base  # ORM 모델 기본 클래스
from sqlalchemy.orm import sessionmaker  # 데이터베이스 세션 팩토리

# 데이터베이스 연결 정보 - .env.global에서 로드되는 PostgreSQL 설정
# 목적: Docker 컨테이너 간 안전한 데이터베이스 연결 설정
# 주의: DB_HOST는 Docker 컨테이너 이름 (uncommon_rag-postgres)
DB_HOST = os.environ["DB_HOST"]  # PostgreSQL 서버 호스트
DB_PORT = os.environ["DB_PORT"]  # PostgreSQL 포트
DB_NAME = os.environ["DB_NAME"]  # 데이터베이스 이름
DB_USER = os.environ["DB_USER"]  # 데이터베이스 사용자
DB_PASSWORD = os.environ["DB_PASSWORD"]  # 데이터베이스 비밀번호

# PostgreSQL 연결 URL 생성 - SQLAlchemy 엔진에서 사용할 연결 문자열
# 형식: postgresql://사용자:비밀번호@호스트:포트/데이터베이스명
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy ORM 기본 설정 - 데이터베이스 엔진 및 세션 설정
# engine: PostgreSQL 연결 담당, SessionLocal: 트랜잭션 세션, Base: 모델 기반 클래스
engine = create_engine(DATABASE_URL)  # PostgreSQL 데이터베이스 엔진 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # 세션 팩토리 설정
Base = declarative_base()  # ORM 모델의 기반 클래스

# 데이터베이스 테이블 초기화 함수 - 서비스 시작 시 혼지 호출
# 목적: models.py에 정의된 모든 테이블을 PostgreSQL에 생성
# 관련 함수: main.py의 startup_event
# 동작: products, product_images, scraping_jobs 테이블 생성 (존재하지 않을 경우)
def init_db():
    """데이터베이스 테이블 초기화 - Base에 등록된 모든 모델의 테이블 생성"""
    Base.metadata.create_all(bind=engine)  # CREATE TABLE IF NOT EXISTS 실행

# 데이터베이스 세션 생성 및 관리 함수 - FastAPI Dependency Injection에서 사용
# 목적: HTTP 요청별로 독립적인 데이터베이스 세션 제공
# 관련 함수: main.py의 start_scraping API 등에서 Depends(get_db) 형태로 사용
# 특징: yield 패턴으로 세션 자동 정리 보장
def get_db():
    """데이터베이스 세션 생성 - 요청 종료 후 자동으로 연결 종료"""
    db = SessionLocal()  # 새 데이터베이스 세션 생성
    try:
        yield db  # FastAPI에 세션 전달
    finally:
        db.close()  # 요청 종료 후 세션 닫기