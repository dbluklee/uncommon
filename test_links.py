#!/usr/bin/env python3
"""
스크래퍼와 동일한 로직으로 제품 링크 추출 테스트
"""
import requests
from bs4 import BeautifulSoup
import random
import time

def get_product_links_like_scraper(base_url):
    """스크래퍼와 동일한 로직으로 제품 링크 추출"""
    
    # 스크래퍼와 동일한 User-Agent 설정
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    
    # 스크래퍼와 동일한 헤더 설정
    session = requests.Session()
    session.headers.update({
        'User-Agent': random.choice(user_agents),
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
    
    all_product_links = []
    page_num = 1
    
    print(f"🔍 스크래퍼 로직으로 제품 링크 추출 시작: {base_url}")
    
    try:
        # 페이지네이션으로 모든 제품 링크 수집 (스크래퍼와 동일)
        while True:
            # 페이지 URL 구성
            page_url = f"{base_url}?page={page_num}"
            print(f"\n📄 페이지 {page_num} 스크래핑 중: {page_url}")
            
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # *** 스크래퍼와 동일한 로직: prdImg div들을 찾아서 제품 링크 추출 ***
            prd_imgs = soup.find_all('div', class_='prdImg')
            
            # prdImg가 하나도 없으면 스크래핑 종료
            if not prd_imgs:
                print(f"❌ 페이지 {page_num}에서 prdImg div를 찾을 수 없음. 스크래핑 종료.")
                break
            
            page_links = []
            for prd_img in prd_imgs:
                # prdImg div 안의 a 태그 찾기
                link = prd_img.find('a', href=True)
                if link:
                    href = link['href']
                    # 상대경로를 절대경로로 변환 (스크래퍼와 동일)
                    if href.startswith('/'):
                        full_url = f"https://ucmeyewear.earth{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        full_url = f"https://ucmeyewear.earth/{href}"
                    
                    # 중복 제거 (스크래퍼와 동일)
                    if full_url not in all_product_links:
                        page_links.append(full_url)
                        all_product_links.append(full_url)
            
            print(f"✅ 페이지 {page_num}: {len(page_links)}개의 새로운 제품 링크 발견")
            
            # 이 페이지의 링크들 출력
            for i, link in enumerate(page_links, 1):
                link_num = len(all_product_links) - len(page_links) + i
                print(f"  {link_num:2d}. {link}")
            
            # 다음 페이지로
            page_num += 1
            
            # 페이지 간 대기 (스크래퍼와 동일)
            delay = random.uniform(2, 5)
            print(f"⏱️  다음 페이지까지 {delay:.1f}초 대기...")
            time.sleep(delay)
        
        print(f"\n📊 총 {len(all_product_links)}개의 고유한 제품 링크를 발견했습니다.")
        return all_product_links
        
    except requests.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        return []
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

if __name__ == "__main__":
    base_url = "https://ucmeyewear.earth/category/all/87/"
    print("🚀 스크래퍼와 동일한 로직으로 제품 링크 추출 테스트 시작\n")
    
    links = get_product_links_like_scraper(base_url)
    
    if links:
        print(f"\n✨ 성공적으로 {len(links)}개 제품 링크를 추출했습니다!")
        print("\n📋 추출된 모든 제품 링크:")
        for i, link in enumerate(links, 1):
            print(f"{i:2d}. {link}")
    else:
        print("\n❌ 제품 링크를 찾을 수 없습니다.")