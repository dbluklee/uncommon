from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

security = HTTPBearer()

# Environment variables
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "admin_secret_key_2024")
TARGET_URL = os.getenv("TARGET_URL", "https://ucmeyewear.earth/category/all/87/")
INDEXING_SERVICE_URL = os.getenv("INDEXING_SERVICE_URL", "http://rag-indexing:8000")

# Pydantic models
class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    max_products: Optional[int] = None  # None이면 모든 제품 스크래핑

class ScrapeResponse(BaseModel):
    job_id: int
    message: str
    target_url: str

class JobStatus(BaseModel):
    job_id: int
    status: str
    products_count: int
    started_at: str
    completed_at: Optional[str] = None

class ProductInfo(BaseModel):
    id: int
    source_url: str
    product_name: str
    color: str
    price: dict  # JSON: {"global": "", "kr": ""}
    reward_points: dict  # JSON: {"global": "", "kr": ""}
    description: dict  # JSON: {"global": "", "kr": ""}
    material: dict  # JSON: {"global": "", "kr": ""}
    size: dict  # JSON: {"global": "", "kr": ""}
    scraped_at: str
    indexed: bool
    image_count: int

class SystemStats(BaseModel):
    total_products: int
    indexed_products: int
    pending_products: int
    total_images: int
    running_jobs: int

# Authentication
def verify_admin_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

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

@app.post("/admin/scrape", response_model=ScrapeResponse)
async def start_scraping(
    request: ScrapeRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """관리자용 스크래핑 시작 API"""
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

@app.get("/admin/jobs", response_model=List[JobStatus])
async def get_scraping_jobs(
    limit: int = 10,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """스크래핑 작업 목록 조회"""
    jobs = db.query(ScrapingJob).order_by(
        ScrapingJob.started_at.desc()
    ).limit(limit).all()
    
    result = []
    for job in jobs:
        result.append(JobStatus(
            job_id=job.id,
            status=job.status,
            products_count=job.products_count,
            started_at=job.started_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        ))
    
    return result

@app.get("/admin/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """특정 스크래핑 작업 상태 조회"""
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(
        job_id=job.id,
        status=job.status,
        products_count=job.products_count,
        started_at=job.started_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )

@app.get("/admin/products", response_model=List[ProductInfo])
async def get_products(
    limit: int = 20,
    indexed: Optional[bool] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """제품 목록 조회"""
    query = db.query(Product)
    
    if indexed is not None:
        query = query.filter(Product.indexed == indexed)
    
    products = query.order_by(Product.scraped_at.desc()).limit(limit).all()
    
    result = []
    for product in products:
        # 이미지 개수 계산
        image_count = db.query(ProductImage).filter(
            ProductImage.product_id == product.id
        ).count()
        
        # 새로운 JSON 구조에서 데이터 추출
        result.append(ProductInfo(
            id=product.id,
            source_url=product.source_url,
            product_name=product.product_name or '',
            color=product.color or '',
            price=product.price or {},  # JSON 형태
            reward_points=product.reward_points or {},  # JSON 형태
            description=product.description or {},  # JSON 형태
            material=product.material or {},  # JSON 형태
            size=product.size or {},  # JSON 형태
            scraped_at=product.scraped_at.isoformat(),
            indexed=product.indexed,
            image_count=image_count
        ))
    
    return result

@app.get("/admin/stats", response_model=SystemStats)
async def get_system_stats(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """시스템 통계 조회"""
    total_products = db.query(Product).count()
    indexed_products = db.query(Product).filter(Product.indexed == True).count()
    pending_products = total_products - indexed_products
    total_images = db.query(ProductImage).count()
    running_jobs = db.query(ScrapingJob).filter(ScrapingJob.status == "running").count()
    
    return SystemStats(
        total_products=total_products,
        indexed_products=indexed_products,
        pending_products=pending_products,
        total_images=total_images,
        running_jobs=running_jobs
    )

@app.delete("/admin/products/{product_id}")
async def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_admin_key)
):
    """제품 삭제 (이미지 포함)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 관련 이미지들은 CASCADE로 자동 삭제됨
    db.delete(product)
    db.commit()
    
    return {"message": f"Product {product_id} deleted successfully"}

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
    uvicorn.run(app, host="0.0.0.0", port=8000)