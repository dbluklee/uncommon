#!/usr/bin/env python3
"""
청킹 결과를 확인하는 테스트 스크립트
"""

import os
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv('.env')

# 프로젝트 모듈 임포트
from database import Product, ProductImage
from text_chunker import ProductTextChunker

def prepare_product_data(product: Product, images):
    """DB 제품 데이터를 청킹에 적합한 형태로 준비"""
    
    # 제품 기본 정보
    product_data = {
        'id': product.id,
        'name': product.product_name,
        'url': product.source_global_url or product.source_kr_url,
        'price': str(product.price) if product.price else '',
        'brand': 'UNCOMMON',
        'category': 'eyewear'
    }
    
    # 모든 제품 정보를 문자열로 합치기
    description_parts = []
    
    # color 정보
    if product.color:
        description_parts.append(f"색상: {product.color}")
    
    # description 정보 (JSON 처리)
    if product.description:
        desc_str = str(product.description)
        if desc_str and desc_str != '{}':
            description_parts.append(f"설명: {desc_str}")
    
    # material 정보 (JSON 처리)  
    if product.material:
        material_str = str(product.material)
        if material_str and material_str != '{}':
            description_parts.append(f"재질: {material_str}")
    
    # size 정보 (JSON 처리)
    if product.size:
        size_str = str(product.size)
        if size_str and size_str != '{}':
            description_parts.append(f"사이즈: {size_str}")
    
    # 설명 통합
    product_data['description'] = " | ".join(description_parts) if description_parts else ""
    
    # 이미지 정보
    if images:
        product_data['images'] = []
        for idx, img in enumerate(images):
            image_info = {
                'image_id': img.id,
                'image_order': img.image_order or idx,
                'size_bytes': len(img.image_data) if img.image_data else 0,
                'alt_text': f"제품 이미지 {idx + 1}",
                'context': f"제품 {product.product_name}의 {idx + 1}번째 이미지"
            }
            product_data['images'].append(image_info)
    
    return product_data

def main():
    # 데이터베이스 연결
    POSTGRES_USER = os.environ['POSTGRES_USER']
    POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD'] 
    POSTGRES_HOST = os.environ['POSTGRES_HOST']
    POSTGRES_DB = os.environ['POSTGRES_DB']
    POSTGRES_PORT = os.environ['POSTGRES_PORT']  # 외부 포트 사용
    
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # 청킹 모듈 초기화
    chunker = ProductTextChunker(chunk_size=500)
    
    # 제품 조회 (ID 2)
    product = db.query(Product).filter(Product.id == 2).first()
    if not product:
        print("❌ 제품 ID 2를 찾을 수 없습니다.")
        return
    
    # 이미지 조회
    images = db.query(ProductImage).filter(ProductImage.product_id == product.id).all()
    
    print(f"🔍 제품 분석: {product.product_name}")
    print(f"📊 제품 ID: {product.id}")
    print(f"🎨 색상: {product.color}")
    print(f"🖼️ 이미지 수: {len(images)}")
    print()
    
    # 제품 데이터 준비
    product_data = prepare_product_data(product, images)
    print("📋 준비된 제품 데이터:")
    print(json.dumps(product_data, indent=2, ensure_ascii=False))
    print()
    
    # 청킹 실행
    chunks = chunker.chunk_product_data(product_data)
    print(f"📦 생성된 청크 수: {len(chunks)}")
    print("=" * 80)
    
    # 각 청크 출력
    for i, chunk in enumerate(chunks, 1):
        print(f"🔵 청크 {i}/{len(chunks)}:")
        print(f"📝 내용:")
        print(chunk.page_content)
        print()
        print(f"🏷️ 메타데이터:")
        print(json.dumps(chunk.metadata, indent=2, ensure_ascii=False))
        print("=" * 80)
    
    db.close()

if __name__ == "__main__":
    main()