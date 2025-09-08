import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from models import Product, ProductImage
from typing import List, Dict, Any, Optional
import json
import os
from urllib.parse import urljoin, urlparse
import time
import random
import io
from PIL import Image
import re
from lxml import etree
from decimal import Decimal
import html

class ProductScraper:
    def __init__(self, db: Session):
        self.db = db
        self.session = requests.Session()
        # 영문/한글 사이트 URL
        self.global_base_url = "https://ucmeyewear.earth/category/all/87/"
        self.kr_base_url = "https://ucmeyewear.com/product/list.html?cate_no=87"
        
        # IP 차단 방지를 위한 User-Agent 로테이션
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        self._update_session_headers()
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        
        # 요청 간격 설정 (IP 차단 방지)
        self.min_delay = 2  # 최소 2초 대기
        self.max_delay = 5  # 최대 5초 대기
    
    def _clean_text(self, text: str) -> str:
        """HTML 엔티티를 디코딩하고 텍스트를 정리"""
        if not text:
            return ""
        
        # HTML 엔티티 디코딩
        cleaned = html.unescape(text)
        
        # 추가 정리 (줄바꿈, 탭, 여러 공백 정리)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
        
    def _update_session_headers(self):
        """세션 헤더 업데이트 (IP 차단 방지)"""
        self.session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0'
        })
    
    def _safe_delay(self):
        """안전한 요청 간격 대기"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    async def scrape_products_both_sites(self, max_products: int = None) -> int:
        """영문과 한글 사이트를 순차적으로 스크래핑"""
        total_scraped = 0
        
        # 1. 영문 사이트 스크래핑
        print("=== 영문 사이트 스크래핑 시작 ===")
        global_count = await self.scrape_products(self.global_base_url, max_products, "global")
        total_scraped += global_count
        print(f"영문 사이트 스크래핑 완료: {global_count}개")
        
        # 2. 한글 사이트 스크래핑
        print("=== 한글 사이트 스크래핑 시작 ===") 
        kr_count = await self.scrape_products(self.kr_base_url, max_products, "kr")
        total_scraped += kr_count
        print(f"한글 사이트 스크래핑 완료: {kr_count}개")
        
        print(f"전체 스크래핑 완료: {total_scraped}개")
        return total_scraped
    
    async def scrape_products(self, target_url: str, max_products: int = None, site_type: str = "global") -> int:
        """모든 페이지에서 제품들을 스크래핑"""
        try:
            print(f"Starting to scrape from: {target_url}")
            
            all_product_links = []
            page_num = 1
            
            # 페이지네이션으로 모든 제품 링크 수집
            while True:
                # 페이지 URL 구성 (사이트별로 다른 형태)
                if site_type == "kr":
                    page_url = f"{target_url}&page={page_num}"
                else:
                    page_url = f"{target_url}?page={page_num}"
                print(f"Scraping page {page_num}: {page_url}")
                
                response = self.session.get(page_url, timeout=self.request_timeout)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # prdImg div들을 찾아서 제품 링크 추출
                prd_imgs = soup.find_all('div', class_='prdImg')
                
                # prdImg가 하나도 없으면 스크래핑 종료
                if not prd_imgs:
                    print(f"No products found on page {page_num}. Ending scraping.")
                    break
                
                page_links = []
                for prd_img in prd_imgs:
                    # prdImg div 안의 a 태그 찾기
                    link = prd_img.find('a', href=True)
                    if link:
                        href = link['href']
                        # 상대경로를 절대경로로 변환 (사이트별 도메인)
                        if href.startswith('/'):
                            if site_type == "kr":
                                full_url = f"https://ucmeyewear.com{href}"
                            else:
                                full_url = f"https://ucmeyewear.earth{href}"
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            if site_type == "kr":
                                full_url = f"https://ucmeyewear.com/{href}"
                            else:
                                full_url = f"https://ucmeyewear.earth/{href}"
                        
                        if full_url not in all_product_links:  # 중복 제거
                            page_links.append(full_url)
                            all_product_links.append(full_url)
                
                print(f"Page {page_num}: Found {len(page_links)} new product links")
                
                # 다음 페이지로
                page_num += 1
                
                # 페이지 간 대기
                self._safe_delay()
            
            print(f"Total unique product links found: {len(all_product_links)}")
            
            if not all_product_links:
                print("No product links found!")
                return 0
            
            # max_products=0인 경우 링크만 출력하고 종료
            if max_products is not None and max_products == 0:
                print(f"=== EXTRACTED PRODUCT LINKS (Total: {len(all_product_links)}) ===")
                for i, link in enumerate(all_product_links, 1):
                    print(f"{i:2d}. {link}")
                print("=== LINK EXTRACTION COMPLETED ===")
                return len(all_product_links)
            
            # 제품 수 제한이 설정된 경우
            products_to_scrape = all_product_links
            if max_products and max_products > 0:
                products_to_scrape = all_product_links[:max_products]
                print(f"Limiting scraping to {max_products} products")
            
            scraped_count = 0
            for i, link in enumerate(products_to_scrape):
                try:
                    print(f"Scraping product {i+1}/{len(products_to_scrape)}: {link}")
                    
                    # IP 차단 방지를 위한 대기
                    if i > 0:
                        self._safe_delay()
                    
                    # User-Agent 로테이션
                    if i % 5 == 0:
                        self._update_session_headers()
                    
                    if self._scrape_single_product(link, site_type):
                        scraped_count += 1
                        print(f"Successfully scraped product {i+1}")
                    else:
                        print(f"Failed to scrape product {i+1}")
                        
                except Exception as e:
                    print(f"Error scraping product {link}: {e}")
                    continue
                    
            print(f"Scraping completed. Total products scraped: {scraped_count}")
            return scraped_count
            
        except Exception as e:
            print(f"Failed to scrape products from {target_url}: {e}")
            return 0
    
    def _scrape_single_product(self, product_url: str, site_type: str = "global") -> bool:
        """단일 제품 페이지 스크래핑"""
        try:
            response = self.session.get(product_url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 제품 정보 추출
            product_data = self._extract_product_info(soup, site_type)
            if not product_data:
                print(f"Could not extract product data from: {product_url}")
                return False
                
            product_name = product_data.get("product_name", "")
            color = product_data.get("color", "")
            
            # 같은 product_name과 color를 가진 기존 제품 찾기
            existing_product = self.db.query(Product).filter(
                Product.product_name == product_name,
                Product.color == color
            ).first()
            
            if existing_product:
                # 기존 제품 업데이트
                print(f"Updating existing product: {product_name} - {color}")
                self._update_existing_product(existing_product, product_url, product_data, site_type)
            else:
                # 새 제품 생성  
                print(f"Creating new product: {product_name} - {color}")
                product = self._create_new_product(product_url, product_data, site_type)
                
                # 이미지는 새 제품일 때만 다운로드
                image_urls = self._extract_image_urls(soup, site_type)
                if image_urls:
                    self._download_and_save_images(product.id, image_urls)
                    print(f"Saved {len(image_urls)} images for product {product.id}")
            
            return True
            
        except Exception as e:
            print(f"Error scraping product {product_url}: {e}")
            return False
    
    def _extract_product_info(self, soup: BeautifulSoup, site_type: str = "global") -> Optional[Dict[str, Any]]:
        """제품 정보 추출 (새로운 JSON 구조)"""
        try:
            # 새로운 JSON 구조 초기화
            product_data = {
                "product_name": "",
                "color": "",
                "price": "",
                "reward_points": "",
                "description": {
                    "description": "",
                    "material": "",
                    "size": {
                        "lens_width": "",
                        "lens_height": "",
                        "bridge_width": "",
                        "frame_width": "",
                        "temple_length": ""
                    }
                },
                "isSoldout": False,
                "contry": "global"
            }
            
            # lxml 파서 준비
            html_str = str(soup)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_str, parser)
            
            # Product Name 추출 - meta keywords 사용
            meta_keywords_xpath = "//meta[@name='keywords']"
            meta_elements = tree.xpath(meta_keywords_xpath)
            
            if meta_elements:
                keywords_content = meta_elements[0].get('content')
                if keywords_content:
                    # 쉼표로 분리하여 첫 번째 텍스트를 가져옴
                    keywords_list = keywords_content.split(',')
                    if keywords_list:
                        first_keyword = keywords_list[0].strip()
                        # '-'를 기준으로 제품명과 색상 분리
                        if ' - ' in first_keyword:
                            parts = first_keyword.split(' - ', 1)
                            product_data["product_name"] = parts[0].strip()
                            product_data["color"] = parts[1].strip()
                        else:
                            product_data["product_name"] = first_keyword
                            product_data["color"] = ""
            
            # 최소한 제품명이 있어야 유효한 데이터로 간주
            if not product_data["product_name"]:
                print("No product name found, skipping...")
                return None
            
            # 가격 추출 - //strong[@id='span_product_price_text']
            price_elements = tree.xpath("//strong[@id='span_product_price_text']")
            if price_elements and price_elements[0].text:
                product_data["price"] = price_elements[0].text
            
            # 리워드 포인트 추출 - //span[@id='span_mileage_text']  
            reward_elements = tree.xpath("//span[@id='span_mileage_text']")
            if reward_elements and reward_elements[0].text:
                product_data["reward_points"] = reward_elements[0].text
            
            # DESCRIPTION 추출 및 처리
            desc_elements = tree.xpath("//p[b[contains(text(), 'DESCRIPTION')]]")
            if desc_elements:
                # 전체 텍스트 내용 가져오기 (innerHTML 형태로)
                desc_html = etree.tostring(desc_elements[0], encoding='unicode')
                # HTML 태그를 줄바꿈으로 변환
                desc_text = re.sub(r'<br\s*/?>', '\n', desc_html)
                # 나머지 HTML 태그 제거
                desc_text = re.sub(r'<[^>]+>', '', desc_text)
                
                # 1. Material 추출
                material_match = re.search(r'-Material\s*:\s*(.+?)(?:\n|$)', desc_text)
                if material_match:
                    product_data["description"]["material"] = self._clean_text(material_match.group(1).strip())
                    # Material 라인 제거
                    desc_text = desc_text.replace(material_match.group(0), '')
                
                # 2. Size 정보 추출
                size_patterns = {
                    'lens_width': r'Lens Width\s*:\s*(.+?)(?:\n|$)',
                    'lens_height': r'Lens Height\s*:\s*(.+?)(?:\n|$)',
                    'bridge_width': r'Bridge [Ww]idth\s*:\s*(.+?)(?:\n|$)',
                    'frame_width': r'Frame [Ww]idth\s*:\s*(.+?)(?:\n|$)',
                    'temple_length': r'Temple Length\s*:\s*(.+?)(?:\n|$)'
                }
                
                for key, pattern in size_patterns.items():
                    match = re.search(pattern, desc_text)
                    if match:
                        product_data["description"]["size"][key] = self._clean_text(match.group(1).strip())
                        # 해당 라인 제거
                        desc_text = desc_text.replace(match.group(0), '')
                
                # 3. SIZE 헤더 제거
                desc_text = re.sub(r'SIZE\s*\n?', '', desc_text)
                
                # 4. Notice 이후 텍스트 제거 (영문 사이트에서만)
                if site_type == "global":
                    notice_match = re.search(r'※Notice.*', desc_text, re.DOTALL)
                    if notice_match:
                        # Notice 이후 모든 텍스트 삭제
                        desc_text = desc_text[:notice_match.start()]
                
                # 5. DESCRIPTION 헤더 제거 및 정리
                desc_text = re.sub(r'DESCRIPTION\s*\n?', '', desc_text)
                desc_text = re.sub(r'\n+', ' ', desc_text)  # 여러 줄바꿈을 공백으로
                desc_text = desc_text.strip()
                
                # 최종 description 저장
                product_data["description"]["description"] = self._clean_text(desc_text)
            
            # 품절 여부 확인 - sold out 버튼 체크
            soldout_xpath = "//span[contains(@class, 'button_left displaynone') and normalize-space()='sold out']"
            soldout_elements = tree.xpath(soldout_xpath)
            
            # soldout_elements가 있으면 아직 판매중 (displaynone이므로 숨겨져 있음)
            if soldout_elements:
                product_data["isSoldout"] = False  # 아직 판매중
                print(f"Product is AVAILABLE: {product_data.get('product_name', 'Unknown')}")
            else:
                product_data["isSoldout"] = True  # 제품 솔드아웃됨
                print(f"Product is SOLD OUT: {product_data.get('product_name', 'Unknown')}")
            
            return product_data
            
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None
    
    def _extract_image_urls(self, soup: BeautifulSoup, site_type: str = "global") -> List[str]:
        """제품 이미지 URL 추출"""
        try:
            # lxml 파서 준비
            html_str = str(soup)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_str, parser)
            
            # XPath로 이미지 추출
            image_xpath = "//div[contains(@class, 'xans-element- xans-product xans-product-addimage swiper-wrapper')]//img[@class='ThumbImage']"
            image_elements = tree.xpath(image_xpath)
            
            image_urls = []
            for img in image_elements:
                src = img.get('src')
                if src:
                    # URL 정규화 - 이중 경로 문제 해결
                    full_url = self._normalize_image_url(src, site_type)
                    if full_url:
                        image_urls.append(full_url)
            
            print(f"Found {len(image_urls)} product images")
            return image_urls
            
        except Exception as e:
            print(f"Error extracting image URLs: {e}")
            return []
    
    def _normalize_image_url(self, src: str, site_type: str = "global") -> Optional[str]:
        """이미지 URL 정규화 - //로 시작하는 경우만 처리"""
        try:
            # //domain/path 형태인 경우 https: 추가
            if src.startswith('//'):
                return f"https:{src}"
            else:
                print(f"Unexpected image URL format: {src}")
                return None
                
        except Exception as e:
            print(f"Error normalizing image URL {src}: {e}")
            return None
    
    def _download_and_save_images(self, product_id: int, image_urls: List[str]):
        """이미지들을 다운로드하고 데이터베이스에 저장"""
        for order, url in enumerate(image_urls):
            try:
                # IP 차단 방지를 위한 이미지 다운로드 간격
                if order > 0:
                    time.sleep(random.uniform(0.5, 1.5))
                
                print(f"Downloading image {order + 1}: {url}")
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                
                # 이미지 데이터 검증
                try:
                    img = Image.open(io.BytesIO(response.content))
                    img.verify()
                except Exception as e:
                    print(f"Invalid image data from {url}: {e}")
                    continue
                
                # 데이터베이스에 저장
                product_image = ProductImage(
                    product_id=product_id,
                    image_data=response.content,
                    image_order=order
                )
                self.db.add(product_image)
                
            except Exception as e:
                print(f"Failed to download image {url}: {e}")
                continue
        
        try:
            self.db.commit()
            print(f"Successfully saved images for product {product_id}")
        except Exception as e:
            print(f"Failed to save images for product {product_id}: {e}")
            self.db.rollback()
    
    
    def _format_description(self, desc_dict: Dict[str, Any]) -> str:
        """설명 딕셔너리를 문자열로 포맷팅"""
        try:
            parts = []
            
            # 기본 설명
            if desc_dict.get("description"):
                parts.append(desc_dict["description"])
            
            # 재질 정보
            if desc_dict.get("material"):
                parts.append(f"Material: {desc_dict['material']}")
            
            # 사이즈 정보
            size_info = desc_dict.get("size", {})
            size_parts = []
            for key, value in size_info.items():
                if value:
                    readable_key = key.replace('_', ' ').title()
                    size_parts.append(f"{readable_key}: {value}")
            
            if size_parts:
                parts.append("Size - " + ", ".join(size_parts))
            
            return " | ".join(parts)
        except:
            return ""
    
    def _create_new_product(self, product_url: str, product_data: Dict[str, Any], site_type: str) -> Product:
        """새 제품 생성"""
        # JSON 필드 초기화
        price_json = {"global": "", "kr": ""}
        reward_points_json = {"global": "", "kr": ""}
        description_json = {"global": "", "kr": ""}
        material_json = {"global": "", "kr": ""}
        size_json = {"global": "", "kr": ""}
        
        # 현재 사이트의 데이터로 채우기
        price_json[site_type] = product_data.get("price", "")
        reward_points_json[site_type] = product_data.get("reward_points", "")
        
        desc_data = product_data.get("description", {})
        description_json[site_type] = desc_data.get("description", "")
        material_json[site_type] = desc_data.get("material", "")
        size_json[site_type] = self._format_size_data(desc_data.get("size", {}))
        
        # URL 필드 설정
        source_global_url = product_url if site_type == "global" else None
        source_kr_url = product_url if site_type == "kr" else None
        
        product = Product(
            source_global_url=source_global_url,
            source_kr_url=source_kr_url,
            product_name=product_data.get("product_name", ""),
            color=product_data.get("color", ""),
            price=price_json,
            reward_points=reward_points_json,
            description=description_json,
            material=material_json,
            size=size_json,
            issoldout=product_data.get("isSoldout", False)
        )
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def _update_existing_product(self, product: Product, product_url: str, product_data: Dict[str, Any], site_type: str):
        """기존 제품 업데이트"""
        # URL 업데이트
        if site_type == "global":
            product.source_global_url = product_url
        else:
            product.source_kr_url = product_url
        
        # 기존 JSON 데이터 가져오기
        price_json = dict(product.price) if product.price else {"global": "", "kr": ""}
        reward_points_json = dict(product.reward_points) if product.reward_points else {"global": "", "kr": ""}
        description_json = dict(product.description) if product.description else {"global": "", "kr": ""}
        material_json = dict(product.material) if product.material else {"global": "", "kr": ""}
        size_json = dict(product.size) if product.size else {"global": "", "kr": ""}
        
        # 현재 사이트의 데이터로 업데이트
        price_json[site_type] = product_data.get("price", "")
        reward_points_json[site_type] = product_data.get("reward_points", "")
        
        desc_data = product_data.get("description", {})
        description_json[site_type] = desc_data.get("description", "")
        material_json[site_type] = desc_data.get("material", "")
        size_json[site_type] = self._format_size_data(desc_data.get("size", {}))
        
        # 데이터베이스 업데이트
        product.price = price_json
        product.reward_points = reward_points_json
        product.description = description_json
        product.material = material_json
        product.size = size_json
        product.issoldout = product_data.get("isSoldout", False)
        
        self.db.commit()
    
    def _format_size_data(self, size_data: Dict[str, str]) -> str:
        """사이즈 데이터를 문자열로 포맷팅"""
        try:
            size_parts = []
            for key, value in size_data.items():
                if value:
                    readable_key = key.replace('_', ' ').title()
                    size_parts.append(f"{readable_key}: {value}")
            return ", ".join(size_parts)
        except:
            return ""