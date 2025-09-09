"""
제품 데이터 청킹 모듈 - UNCOMMON 프로젝트 특화
제품 정보를 의미 있는 단위로 청킹
"""

import logging
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

class ProductChunk:
    """제품 청크 객체"""
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

class ProductTextChunker:
    """제품 데이터 전용 청킹 클래스"""
    
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size
    
    def chunk_product_data(self, product_data: Dict[str, Any]) -> List[ProductChunk]:
        """
        제품 데이터를 의미 있는 청크로 분할
        """
        chunks = []
        
        # 제품 기본 정보 청크
        basic_info = self._create_basic_info_chunk(product_data)
        if basic_info:
            chunks.append(basic_info)
        
        # 제품 상세 설명 청크
        description_chunks = self._create_description_chunks(product_data)
        chunks.extend(description_chunks)
        
        # 이미지 컨텍스트 청크
        image_chunks = self._create_image_chunks(product_data)
        chunks.extend(image_chunks)
        
        logger.info(f"Generated {len(chunks)} chunks for product {product_data.get('id', 'unknown')}")
        return chunks
    
    def _create_basic_info_chunk(self, product_data: Dict[str, Any]) -> ProductChunk:
        """제품 기본 정보 청크 생성"""
        content_parts = []
        
        # 제품 기본 정보 구성
        content_parts.append("=== 제품 기본 정보 ===")
        
        if product_data.get('name'):
            content_parts.append(f"제품명: {product_data['name']}")
        
        if product_data.get('price'):
            content_parts.append(f"가격: {product_data['price']}")
        
        if product_data.get('brand'):
            content_parts.append(f"브랜드: {product_data['brand']}")
        
        if product_data.get('category'):
            content_parts.append(f"카테고리: {product_data['category']}")
        
        # JSON 형태 정보 파싱
        try:
            if isinstance(product_data.get('data'), str):
                data = json.loads(product_data['data'])
            else:
                data = product_data.get('data', {})
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in ['material', 'features', 'specifications', 'dimensions']:
                        content_parts.append(f"{key}: {value}")
        except (json.JSONDecodeError, Exception):
            pass
        
        if not content_parts or len(content_parts) <= 1:
            return None
        
        page_content = "\n".join(content_parts)
        
        metadata = {
            'source': 'product_basic_info',
            'product_id': product_data.get('id'),
            'product_name': product_data.get('name', ''),
            'chunk_type': 'basic_info',
            'url': product_data.get('url', '')
        }
        
        return ProductChunk(page_content=page_content, metadata=metadata)
    
    def _create_description_chunks(self, product_data: Dict[str, Any]) -> List[ProductChunk]:
        """제품 설명 청크 생성"""
        chunks = []
        
        # 제품 설명이 있는 경우
        description = product_data.get('description', '')
        if not description:
            return chunks
        
        # 긴 설명의 경우 분할
        if len(description.split()) > self.chunk_size:
            # 단락별로 분할 시도
            paragraphs = description.split('\n\n')
            current_chunk = ""
            
            for paragraph in paragraphs:
                if len((current_chunk + paragraph).split()) <= self.chunk_size:
                    current_chunk += paragraph + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(self._create_description_chunk(current_chunk.strip(), product_data))
                    current_chunk = paragraph + "\n\n"
            
            # 마지막 청크 처리
            if current_chunk:
                chunks.append(self._create_description_chunk(current_chunk.strip(), product_data))
        else:
            chunks.append(self._create_description_chunk(description, product_data))
        
        return chunks
    
    def _create_description_chunk(self, description: str, product_data: Dict[str, Any]) -> ProductChunk:
        """설명 청크 생성"""
        content_parts = []
        content_parts.append("=== 제품 설명 ===")
        content_parts.append(f"제품명: {product_data.get('name', '')}")
        content_parts.append("")
        content_parts.append(description)
        
        page_content = "\n".join(content_parts)
        
        metadata = {
            'source': 'product_description',
            'product_id': product_data.get('id'),
            'product_name': product_data.get('name', ''),
            'chunk_type': 'description',
            'url': product_data.get('url', '')
        }
        
        return ProductChunk(page_content=page_content, metadata=metadata)
    
    def _create_image_chunks(self, product_data: Dict[str, Any]) -> List[ProductChunk]:
        """이미지 컨텍스트 청크 생성"""
        chunks = []
        
        # 이미지 정보가 있는 경우
        if not product_data.get('images'):
            return chunks
        
        images = product_data['images']
        
        # 이미지가 많을 경우 그룹화
        batch_size = 5  # 한 청크에 5개 이미지씩
        
        for i in range(0, len(images), batch_size):
            batch_images = images[i:i+batch_size]
            
            content_parts = []
            content_parts.append("=== 제품 이미지 정보 ===")
            content_parts.append(f"제품명: {product_data.get('name', '')}")
            content_parts.append("")
            
            for idx, image in enumerate(batch_images, 1):
                content_parts.append(f"이미지 {i+idx}:")
                if image.get('alt_text'):
                    content_parts.append(f"  설명: {image['alt_text']}")
                if image.get('context'):
                    content_parts.append(f"  맥락: {image['context']}")
                if image.get('size_bytes'):
                    content_parts.append(f"  크기: {image['size_bytes']} bytes")
                content_parts.append("")
            
            page_content = "\n".join(content_parts)
            
            metadata = {
                'source': 'product_images',
                'product_id': product_data.get('id'),
                'product_name': product_data.get('name', ''),
                'chunk_type': 'images',
                'image_count': len(batch_images),
                'url': product_data.get('url', '')
            }
            
            chunks.append(ProductChunk(page_content=page_content, metadata=metadata))
        
        return chunks