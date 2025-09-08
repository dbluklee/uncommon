#!/usr/bin/env python3
"""
UNCOMMON 스크래핑 테스트 파일
- 기본 구조 테스트용
- 나중에 동작 확인 후 삭제 예정
"""

import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, Any, Optional, List

class TestScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://ucmeyewear.earth/category/all/87/"
        
        # 기본 헤더 설정
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_product_links(self) -> List[str]:
        """모든 페이지에서 제품 링크들을 가져오기"""
        all_product_links = []
        page_num = 1
        
        while True:
            # 페이지 URL 구성
            page_url = f"{self.base_url}?page={page_num}"
            print(f"Fetching page {page_num}: {page_url}")
            
            response = self.session.get(page_url)
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
                    # 상대경로를 절대경로로 변환
                    if href.startswith('/'):
                        full_url = f"https://ucmeyewear.earth{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://ucmeyewear.earth/{href}"
                    
                    if full_url not in all_product_links:  # 중복 제거
                        page_links.append(full_url)
                        all_product_links.append(full_url)
            
            print(f"Page {page_num}: Found {len(page_links)} new product links")
            
            # 다음 페이지로
            page_num += 1
        
        print(f"Total unique product links found: {len(all_product_links)}")
        return all_product_links
    
    def scrape_product(self, product_url: str) -> Optional[Dict[str, Any]]:
        """단일 제품 정보 스크래핑"""
        try:
            print(f"Scraping product: {product_url}")
            response = self.session.get(product_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 목표 JSON 구조
            product_data = {
                "product_name": "",
                "color": "",
                "price": 0.0,
                "reward_points": {
                    "amount": 0.0,
                    "percentage": 0
                },
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
            
            # Product Name 추출 및 색상 분리
            full_product_name = self.extract_product_name(soup)
            if full_product_name and ' - ' in full_product_name:
                # '-'를 기준으로 제품명과 색상 분리
                parts = full_product_name.split(' - ', 1)
                product_data["product_name"] = parts[0].strip()
                product_data["color"] = parts[1].strip()
                print(f"Separated - Product Name: {product_data['product_name']}, Color: {product_data['color']}")
            else:
                # '-'가 없으면 전체를 제품명으로
                product_data["product_name"] = full_product_name
                product_data["color"] = ""
            
            # lxml 파서 준비
            from lxml import etree
            html_str = str(soup)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_str, parser)
            
            # 가격 추출 - //strong[@id='span_product_price_text']
            price_elements = tree.xpath("//strong[@id='span_product_price_text']")
            if price_elements and price_elements[0].text:
                product_data["price"] = price_elements[0].text
                print(f"Found price: {product_data['price']}")
            
            # 리워드 포인트 추출 - //span[@id='span_mileage_text']  
            reward_elements = tree.xpath("//span[@id='span_mileage_text']")
            if reward_elements and reward_elements[0].text:
                product_data["reward_points"] = reward_elements[0].text
                print(f"Found reward: {product_data['reward_points']}")
            
            # DESCRIPTION 추출 및 처리
            desc_elements = tree.xpath("//p[b[contains(text(), 'DESCRIPTION')]]")
            if desc_elements:
                # 전체 텍스트 내용 가져오기 (innerHTML 형태로)
                desc_html = etree.tostring(desc_elements[0], encoding='unicode')
                # HTML 태그를 줄바꿈으로 변환
                import re
                desc_text = re.sub(r'<br\s*/?>', '\n', desc_html)
                # 나머지 HTML 태그 제거
                desc_text = re.sub(r'<[^>]+>', '', desc_text)
                
                # 1. Material 추출
                material_match = re.search(r'-Material\s*:\s*(.+?)(?:\n|$)', desc_text)
                if material_match:
                    product_data["description"]["material"] = material_match.group(1).strip()
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
                        product_data["description"]["size"][key] = match.group(1).strip()
                        # 해당 라인 제거
                        desc_text = desc_text.replace(match.group(0), '')
                
                # 3. SIZE 헤더 제거
                desc_text = re.sub(r'SIZE\s*\n?', '', desc_text)
                
                # 4. Notice 이후 텍스트 제거 (저장하지 않음)
                notice_match = re.search(r'※Notice.*', desc_text, re.DOTALL)
                if notice_match:
                    # Notice 이후 모든 텍스트 삭제
                    desc_text = desc_text[:notice_match.start()]
                
                # 5. DESCRIPTION 헤더 제거 및 정리
                desc_text = re.sub(r'DESCRIPTION\s*\n?', '', desc_text)
                desc_text = re.sub(r'\n+', ' ', desc_text)  # 여러 줄바꿈을 공백으로
                desc_text = desc_text.strip()
                
                # 최종 description 저장
                product_data["description"]["description"] = desc_text
                
                print(f"Found description: {desc_text[:100]}...")
                print(f"Found material: {product_data['description']['material']}")
                print(f"Found size info: {product_data['description']['size']}")
            
            # 이미지 URL 추출
            image_xpath = "//div[contains(@class, 'xans-element- xans-product xans-product-addimage swiper-wrapper')]//img[@class='ThumbImage']"
            image_elements = tree.xpath(image_xpath)
            image_urls = []
            for img in image_elements:
                src = img.get('src')
                if src:
                    # 상대경로를 절대경로로 변환
                    if src.startswith('/'):
                        full_url = f"https://ucmeyewear.earth{src}"
                    elif not src.startswith('http'):
                        full_url = f"https://ucmeyewear.earth/{src}"
                    else:
                        full_url = src
                    image_urls.append(full_url)
            
            print(f"Found {len(image_urls)} product images")
            product_data["images"] = image_urls  # 임시로 images 필드에 저장
            
            return product_data
            
        except Exception as e:
            print(f"Error scraping product {product_url}: {e}")
            return None
    
    def extract_product_name(self, soup: BeautifulSoup) -> str:
        """Product Name 추출 - XPath 사용"""
        try:
            from lxml import etree
            
            # BeautifulSoup HTML을 lxml로 파싱
            html_str = str(soup)
            parser = etree.HTMLParser()
            tree = etree.fromstring(html_str, parser)
            
            # XPath로 Product Name 찾기
            xpath = "//th[span[contains(text(), 'Product Name')]]/following-sibling::td[1]/span[1]"
            elements = tree.xpath(xpath)
            
            if elements:
                product_name = elements[0].text
                if product_name:
                    print(f"Found product name via XPath: {product_name}")
                    return product_name.strip()
            
            print("Product name not found via XPath")
            return ""
            
        except Exception as e:
            print(f"Error extracting product name: {e}")
            return ""
    
    def extract_color(self, soup: BeautifulSoup) -> str:
        """색상 정보 추출"""
        # TODO: 구현 예정
        return ""
    
    def extract_price(self, soup: BeautifulSoup) -> float:
        """가격 정보 추출"""
        # TODO: 구현 예정
        return 0.0
    
    def extract_reward_points(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """리워드 포인트 추출"""
        # TODO: 구현 예정
        return {"amount": 0.0, "percentage": 0}
    
    def extract_description_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """설명 정보 전체 추출"""
        # TODO: 구현 예정
        return {
            "description": "",
            "material": "",
            "size": {},
            "notice": ""
        }
    
    def extract_soldout_status(self, soup: BeautifulSoup) -> bool:
        """품절 상태 확인"""
        # TODO: 구현 예정
        return False

def main():
    """테스트 실행 - 제품 링크만 출력"""
    scraper = TestScraper()
    
    print("=== UNCOMMON 제품 링크 추출 테스트 ===\n")
    
    # 제품 링크 가져오기만 테스트
    links = scraper.get_product_links()
    
    if links:
        print(f"\n=======================================")
        print(f"총 {len(links)}개 제품 발견")
        print(f"=======================================\n")
        print("모든 제품 상세 페이지 링크:")
        for i, link in enumerate(links, 1):
            print(f"  {i:3d}. {link}")
    else:
        print("제품 링크를 찾을 수 없습니다")
    
    print(f"\n=== 테스트 완료 (총 {len(links)}개 링크) ===")

if __name__ == "__main__":
    main()