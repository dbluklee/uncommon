-- RAG System Database Schema for Product Data (MVP)

-- Products table for storing scraped product information
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    source_url TEXT NOT NULL,           -- 스크래핑한 페이지 URL
    product_name TEXT NOT NULL,         -- 제품명
    color TEXT,                         -- 색상
    price DECIMAL(10, 2),              -- 가격
    reward_points INTEGER DEFAULT 0,    -- 리워드 포인트
    description TEXT,                   -- 제품 설명
    isSoldout BOOLEAN DEFAULT FALSE,    -- 품절 여부
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