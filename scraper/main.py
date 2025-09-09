from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import os
from database import init_db, get_db
from models import Product, ProductImage, ScrapingJob
from scraper import ProductScraper
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import asyncio
import httpx
from datetime import datetime

app = FastAPI(
    title="RAG Scraper Service",
    description="Product scraping service for RAG LLM system",
    version="1.0.0"
)

# Environment variables
TARGET_URL = os.environ["TARGET_URL"]
INDEXING_SERVICE_HOST = os.environ["INDEXING_SERVICE_HOST"]
INDEXING_SERVICE_PORT = os.environ["INDEXING_SERVICE_PORT"]
INDEXING_SERVICE_URL = f"http://{INDEXING_SERVICE_HOST}:{INDEXING_SERVICE_PORT}"

# Pydantic models
class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    max_products: Optional[int] = None  # None이면 모든 제품 스크래핑

class ScrapeResponse(BaseModel):
    job_id: int
    message: str
    target_url: str

# Removed admin-related models for MVP

# Application Events
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Scraper service started successfully")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "scraper",
        "target_url": TARGET_URL
    }

@app.post("/scrape", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
):
    """제품 스크래핑 시작 API"""
    target_url = request.url or TARGET_URL
    
    # 이미 실행 중인 작업이 있는지 확인
    running_job = db.query(ScrapingJob).filter(
        ScrapingJob.status == "running"
    ).first()
    
    if running_job:
        raise HTTPException(
            status_code=400, 
            detail=f"스크래핑 작업이 이미 실행 중입니다. Job ID: {running_job.id}"
        )
    
    # Create scraping job
    job = ScrapingJob(
        target_url=target_url,
        status="pending"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start scraping in background
    asyncio.create_task(run_scraping(job.id, target_url, request.max_products))
    
    return ScrapeResponse(
        job_id=job.id,
        message="스크래핑이 시작되었습니다",
        target_url=target_url
    )

# Admin endpoints removed for MVP

async def run_scraping(job_id: int, target_url: str, max_products: Optional[int]):
    """백그라운드에서 실행되는 스크래핑 작업"""
    from database import SessionLocal  # 백그라운드 태스크용 별도 세션
    
    db = SessionLocal()
    try:
        # Update job status
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if not job:
            print(f"Job {job_id} not found")
            return
            
        job.status = "running"
        db.commit()
        
        print(f"Starting scraping job {job_id} for URL: {target_url}")
        
        # Run scraper
        scraper = ProductScraper(db)
        products_count = await scraper.scrape_products_both_sites(max_products)
        
        # Update job completion
        job.status = "completed"
        job.products_count = products_count
        job.completed_at = datetime.now()
        db.commit()
        
        print(f"Scraping job {job_id} completed. Products scraped: {products_count}")
        
        # Notify indexing service
        if products_count > 0:
            await notify_indexing_service(products_count)
        
    except Exception as e:
        # Update job error
        print(f"Scraping job {job_id} failed: {e}")
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = datetime.now()
            db.commit()
    finally:
        db.close()

async def notify_indexing_service(products_count: int):
    """스크래핑 완료를 Indexing 서비스에 알림"""
    try:
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ["SCRAPER_INTERNAL_PORT"])
    uvicorn.run(app, host="0.0.0.0", port=port)