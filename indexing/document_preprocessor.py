"""
문서 전처리 모듈 - MVP 버전
PostgreSQL 제품 데이터를 단순 텍스트로 변환
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DocumentPreprocessor:
    """제품 데이터를 문서로 변환"""
    
    def process_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """제품을 문서로 변환"""
        
        # 텍스트 조합
        text_parts = []
        
        # 기본 정보
        if product.get('name'):
            text_parts.append(f"제품명: {product['name']}")
        if product.get('price'):
            text_parts.append(f"가격: {product['price']}")
        if product.get('material'):
            text_parts.append(f"재질: {product['material']}")
        if product.get('features'):
            text_parts.append(f"특징: {product['features']}")
        if product.get('description'):
            text_parts.append(f"설명: {product['description']}")
        
        # JSON 데이터 파싱
        if product.get('product_data'):
            try:
                data = json.loads(product['product_data'])
                if data.get('details'):
                    text_parts.append(f"상세: {' '.join(data['details'])}")
                if data.get('spec_items'):
                    text_parts.append(f"사양: {' '.join(data['spec_items'])}")
            except:
                pass
        
        # 문서 생성
        document = {
            'product_id': product['id'],
            'text': ' | '.join(text_parts),
            'metadata': {
                'name': product.get('name'),
                'url': product.get('url')
            }
        }
        
        return document
    
    def process_batch(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """배치 처리"""
        documents = []
        for product in products:
            try:
                doc = self.process_product(product)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Error processing product {product.get('id')}: {e}")
        return documents