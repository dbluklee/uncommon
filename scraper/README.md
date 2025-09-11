# Scraper 서비스

## 📋 개요
UNCOMMON 아이웨어 웹사이트에서 제품 정보를 자동으로 수집하는 웹 스크래핑 서비스입니다. FastAPI 기반으로 구축되었으며, 제품 데이터와 이미지를 PostgreSQL에 저장합니다.

## 🎯 주요 기능
- **웹 스크래핑**: UNCOMMON 웹사이트 제품 정보 자동 수집
- **이미지 처리**: 제품 이미지 다운로드 및 바이너리 저장
- **데이터 검증**: 중복 제품 체크 및 데이터 무결성 보장
- **작업 관리**: 스크래핑 작업 상태 추적 및 진행률 모니터링

## 🚀 실행 방법

### 환경변수
```bash
SCRAPER_PORT=8001                    # 외부 접근 포트
SCRAPER_INTERNAL_PORT=8000          # 컨테이너 내부 포트
TARGET_URL=https://ucmeyewear.earth/category/all/87/
```

### 실행 명령
```bash
# 서비스 시작
cd scraper
source ../.env.global
docker compose up -d

# 로컬 개발 실행
pip install -r requirements.txt
python main.py
```

### 접속 정보
- **API 서버**: `http://localhost:8001`
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## 📡 API 엔드포인트

### 1. 헬스체크
```http
GET /health
```

**응답 예시:**
```json
{
    "status": "healthy",
    "service": "scraper",
    "timestamp": "2024-01-10T10:30:00Z"
}
```

### 2. 스크래핑 시작
```http
POST /scrape
Content-Type: application/json

{
    "target_url": "https://ucmeyewear.earth/category/all/87/"
}
```

**응답 예시:**
```json
{
    "job_id": 123,
    "message": "스크래핑 작업이 시작되었습니다",
    "target_url": "https://ucmeyewear.earth/category/all/87/",
    "status": "running"
}
```

### 3. 작업 상태 확인
```http
GET /scrape/job/{job_id}
```

**응답 예시:**
```json
{
    "id": 123,
    "target_url": "https://ucmeyewear.earth/category/all/87/",
    "status": "completed",
    "products_count": 25,
    "started_at": "2024-01-10T10:30:00Z",
    "completed_at": "2024-01-10T10:32:15Z"
}
```

## 📊 입력/출력 데이터 형식

### 입력 데이터
```json
{
    "target_url": "https://ucmeyewear.earth/category/all/87/"
}
```

### 출력 데이터 (PostgreSQL 저장)
```python
# Product 데이터 구조
{
    "id": 123,
    "source_global_url": "https://ucmeyewear.earth/products/frame-001",
    "source_kr_url": "https://ucmeyewear.earth/ko/products/frame-001",
    "product_name": "UNCOMMON Titanium Frame",
    "color": "Black",
    "price": {
        "global": "$199.00",
        "kr": "259,000원"
    },
    "reward_points": {
        "global": "199 points",
        "kr": "2,590 포인트"
    },
    "description": {
        "global": "Premium titanium eyewear frame with acetate temples",
        "kr": "아세테이트 템플이 있는 프리미엄 티타늄 아이웨어 프레임"
    },
    "material": {
        "global": "Titanium, Acetate",
        "kr": "티타늄, 아세테이트"
    },
    "size": {
        "global": "Medium (52-18-145)",
        "kr": "미디엄 (52-18-145)"
    },
    "issoldout": false,
    "indexed": false,
    "scraped_at": "2024-01-10T10:30:00Z"
}

# Product Image 데이터 구조  
{
    "id": 456,
    "product_id": 123,
    "image_data": b"\\x89PNG\\r\\n...",  # 바이너리 이미지 데이터
    "image_order": 0
}
```

## 🔄 통신 방식

### HTTP REST API
- **프로토콜**: HTTP/1.1
- **포맷**: JSON
- **인코딩**: UTF-8
- **인증**: 없음 (MVP 단계)

### 데이터베이스 연동
- **ORM**: SQLAlchemy 2.0.23
- **연결**: 비동기 PostgreSQL 연결
- **트랜잭션**: 자동 커밋/롤백

### 외부 웹사이트 통신
```python
# HTTP 요청 설정
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive'
}

# 요청 간 딜레이
sleep_time = random.uniform(1, 3)  # 1-3초 랜덤 딜레이
```

## 🔗 의존성

### 필수 의존성
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
requests==2.31.0
beautifulsoup4==4.12.2
Pillow==10.1.0
python-multipart==0.0.6
```

### 시스템 의존성
- **Python 3.11+**
- **PostgreSQL 데이터베이스**: 제품 데이터 저장
- **Docker & Docker Compose**: 컨테이너 실행 환경

### 연관 서비스
- **PostgreSQL DB**: 스크래핑된 데이터 저장
- **Indexing Service**: 스크래핑 완료 후 벡터 인덱싱 트리거

## 🛠️ 스크래핑 로직

### 1. 제품 목록 수집
```python
def scrape_product_list(category_url):
    # 카테고리 페이지에서 제품 URL 수집
    response = requests.get(category_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    product_links = []
    for link in soup.find_all('a', class_='product-item'):
        product_url = urljoin(category_url, link.get('href'))
        product_links.append(product_url)
    
    return product_links
```

### 2. 개별 제품 정보 수집
```python
def scrape_product_detail(product_url):
    response = requests.get(product_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    product_data = {
        'product_name': soup.find('h1', class_='product-title').text.strip(),
        'color': soup.find('span', class_='color-name').text.strip(),
        'price': extract_price_info(soup),
        'description': extract_description(soup),
        'material': extract_material_info(soup),
        'size': extract_size_info(soup),
        'images': extract_image_urls(soup)
    }
    
    return product_data
```

### 3. 이미지 다운로드 및 저장
```python
def download_and_save_images(product_id, image_urls):
    for order, img_url in enumerate(image_urls):
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            # 이미지를 바이너리로 저장
            image_data = img_response.content
            save_product_image(product_id, image_data, order)
```

## 📈 성능 및 모니터링

### 스크래핑 성능
- **처리 속도**: 제품당 2-3초
- **동시 처리**: 순차 처리 (사이트 부하 방지)
- **재시도 로직**: 실패 시 최대 3회 재시도

### 에러 처리
```python
try:
    product_data = scrape_product_detail(url)
    save_product(product_data)
except requests.RequestException as e:
    logger.error(f"Network error: {e}")
    retry_count += 1
except Exception as e:
    logger.error(f"Parsing error: {e}")
    skip_product()
```

### 로깅 및 모니터링
```python
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 진행상황 로깅
logger.info(f"스크래핑 시작: {target_url}")
logger.info(f"제품 수집 완료: {product_count}개")
logger.info(f"이미지 다운로드: {image_count}개")
```

## ⚠️ 주의사항
- **웹사이트 정책**: robots.txt 준수 및 과도한 요청 방지
- **법적 고려사항**: 저작권 및 이용약관 준수 필요
- **데이터 품질**: 스크래핑된 데이터 검증 및 정제 과정 필요
- **사이트 변경**: 웹사이트 구조 변경 시 파싱 로직 업데이트 필요
- **에러 복구**: 네트워크 오류 및 파싱 오류에 대한 적절한 처리