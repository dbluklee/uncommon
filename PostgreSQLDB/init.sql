-- RAG System Database Schema for Product Data (MVP)

-- Products table for storing scraped product information
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,           -- 스크래핑한 페이지 URL
    product_data JSONB NOT NULL,        -- 제품 정보 JSON (가격, 재질, 특징 등)
    indexed BOOLEAN DEFAULT FALSE,      -- 벡터DB 인덱싱 여부
    scraped_at TIMESTAMP DEFAULT NOW(),
    indexed_at TIMESTAMP
);

-- Product images table for storing multiple images per product
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,          -- 이미지 바이너리 데이터
    image_order INTEGER DEFAULT 0       -- 이미지 순서
);

-- Scraping jobs for tracking scraping operations
CREATE TABLE scraping_jobs (
    id SERIAL PRIMARY KEY,
    target_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    products_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Create basic indexes
CREATE INDEX idx_products_indexed ON products(indexed);
CREATE INDEX idx_product_images_product_id ON product_images(product_id);