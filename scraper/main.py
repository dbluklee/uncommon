# RAG LLM 시스템의 제품 스크래핑 서비스 메인 파일
# 목적: UNCOMMON 안경 쇼핑몰에서 제품 데이터를 자동으로 수집하는 FastAPI 웹 서비스
# 관련 함수: init_db (database.py), ProductScraper.scrape_products_both_sites (scraper.py)
# 의존성: models.py의 ScrapingJob, database.py의 PostgreSQL 연결

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import os
from database import init_db, get_db  # PostgreSQL 데이터베이스 초기화 및 세션 관리
from models import Product, ProductImage, ScrapingJob  # 제품, 이미지, 스크래핑 작업 모델
from scraper import ProductScraper  # 실제 웹 스크래핑 로직
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import asyncio  # 백그라운드 비동기 스크래핑 작업 실행
import httpx  # Indexing 서비스에 HTTP 요청 전송
from datetime import datetime

# FastAPI 애플리케이션 초기화 - RAG 시스템의 스크래핑 서비스
# 목적: 제품 데이터 수집을 위한 RESTful API 제공
app = FastAPI(
    title="RAG Scraper Service",
    description="Product scraping service for RAG LLM system",
    version="1.0.0"
)

# 환경변수 설정 - .env.global에서 로드되는 중요 설정값들
# TARGET_URL: 스크래핑할 UNCOMMON 쇼핑몰 URL
# INDEXING_SERVICE: 스크래핑 완료 후 벡터 인덱싱을 담당하는 서비스 주소
TARGET_URL = os.environ["TARGET_URL"]
INDEXING_SERVICE_HOST = os.environ["INDEXING_SERVICE_HOST"]
INDEXING_SERVICE_PORT = os.environ["INDEXING_SERVICE_PORT"]
INDEXING_SERVICE_URL = f"http://{INDEXING_SERVICE_HOST}:{INDEXING_SERVICE_PORT}"

# API 요청/응답 모델 정의 - 클라이언트와 서버 간 데이터 구조 명세
# ScrapeRequest: 스크래핑 요청 시 받을 파라미터 (URL, 최대 제품 수)
# ScrapeResponse: 스크래핑 작업 시작 후 반환할 정보 (작업 ID, 상태 메시지)
class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    max_products: Optional[int] = None  # None이면 모든 제품 스크래핑

class ScrapeResponse(BaseModel):
    job_id: int
    message: str
    target_url: str

# Removed admin-related models for MVP

# 애플리케이션 생명주기 이벤트 - 서비스 시작 시 필요한 초기화 작업
# 목적: PostgreSQL 데이터베이스 테이블 생성 및 연결 확인
# 관련 함수: init_db (database.py)
@app.on_event("startup")
async def startup_event():
    init_db()  # PostgreSQL 테이블 생성 (products, product_images, scraping_jobs)
    print("Scraper service started successfully")

# 헬스체크 엔드포인트 - 서비스 상태 모니터링
# 목적: Docker 컨테이너 및 로드밸런서에서 서비스 생존 여부 확인
# 응답: 서비스 상태, 타겟 URL 정보
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "scraper",
        "target_url": TARGET_URL
    }

# 메인 스크래핑 API - 웹 스크래핑 작업을 시작하는 핵심 엔드포인트
# 목적: 사용자 요청에 따라 UNCOMMON 사이트에서 제품 데이터 수집 시작
# 관련 함수: run_scraping (백그라운드 작업), ScrapingJob (models.py)
# 동작: 중복 실행 방지 → 작업 생성 → 비동기 스크래핑 시작 → 즉시 응답
@app.post("/scrape", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
):
    """제품 스크래핑 시작 API - UNCOMMON 사이트에서 제품 정보 수집"""
    target_url = request.url or TARGET_URL
    
    # 동시 실행 방지: 이미 실행 중인 스크래핑 작업 확인
    running_job = db.query(ScrapingJob).filter(
        ScrapingJob.status == "running"
    ).first()
    
    if running_job:
        raise HTTPException(
            status_code=400, 
            detail=f"스크래핑 작업이 이미 실행 중입니다. Job ID: {running_job.id}"
        )
    
    # 새 스크래핑 작업 생성 및 데이터베이스 저장
    job = ScrapingJob(
        target_url=target_url,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # 백그라운드에서 실제 스크래핑 작업 시작 (비동기)
    asyncio.create_task(run_scraping(job.id, target_url, request.max_products))
    
    return ScrapeResponse(
        job_id=job.id,
        message="스크래핑이 시작되었습니다",
        target_url=target_url
    )

# Admin endpoints removed for MVP

# 백그라운드 스크래핑 작업 실행 함수 - 실제 웹 스크래핑을 담당하는 핵심 로직
# 목적: API 응답 후 별도 스레드에서 긴 시간이 소요되는 스크래핑 작업 수행
# 관련 함수: ProductScraper.scrape_products_both_sites (scraper.py), notify_indexing_service
# 동작: 작업 상태 업데이트 → 스크래핑 실행 → 결과 저장 → Indexing 서비스 알림
async def run_scraping(job_id: int, target_url: str, max_products: Optional[int]):
    """백그라운드에서 실행되는 스크래핑 작업 - 영문/한글 두 사이트 동시 수집"""
    from database import SessionLocal  # 백그라운드 태스크용 별도 데이터베이스 세션
    
    db = SessionLocal()
    try:
        # 스크래핑 작업 상태를 'running'으로 업데이트
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return
            
        job.status = "running"
        db.commit()
        
        print(f"Starting scraping job {job_id} for URL: {target_url}")
        
        # 실제 스크래핑 실행 - ProductScraper 클래스 활용
        scraper = ProductScraper(db)
        products_count = await scraper.scrape_products_both_sites(max_products)
        
        # 스크래핑 완료 후 작업 상태 및 결과 업데이트
        job.status = "completed"
        job.products_count = products_count
        job.completed_at = datetime.now()
        db.commit()
        
        print(f"Scraping job {job_id} completed. Products scraped: {products_count}")
        
        # 수집된 제품이 있으면 Indexing 서비스에 벡터화 요청
        if products_count > 0:
            await notify_indexing_service(products_count)
        
    except Exception as e:
        # 스크래핑 실패 시 에러 상태 업데이트
        print(f"Scraping job {job_id} failed: {e}")
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = datetime.now()
            db.commit()
    finally:
        db.close()

# Indexing 서비스 알림 함수 - 마이크로서비스 간 통신
# 목적: 스크래핑 완료 후 Indexing 서비스에 새 제품 벡터화 작업 요청
# 관련 서비스: indexing/main.py의 /process/new-products 엔드포인트
# HTTP 통신: 비동기 POST 요청으로 서비스 간 데이터 전달
async def notify_indexing_service(products_count: int):
    """스크래핑 완료를 Indexing 서비스에 알림 - BGE-M3 벡터화 작업 트리거"""
    try:
        # 비동기 HTTP 클라이언트로 Indexing 서비스에 POST 요청
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{INDEXING_SERVICE_URL}/process/new-products",
                json={"products_count": products_count}
            )
            if response.status_code == 200:
                print(f"Successfully notified indexing service: {products_count} products")
            else:
                print(f"Failed to notify indexing service: {response.status_code}")
    except Exception as e:
        print(f"Failed to notify indexing service: {e}")

# 서비스 시작 진입점 - Docker 컨테이너에서 실행되는 메인 함수
# 목적: Uvicorn ASGI 서버로 FastAPI 애플리케이션 실행
# 설정: 모든 네트워크 인터페이스에서 접근 가능 (host="0.0.0.0")
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ["SCRAPER_INTERNAL_PORT"])  # Docker 내부 포트 (8000)
    uvicorn.run(app, host="0.0.0.0", port=port)