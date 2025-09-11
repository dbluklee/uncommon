# PostgreSQL 데이터베이스

## 📋 개요
UNCOMMON RAG 시스템의 핵심 관계형 데이터베이스로, 제품 정보와 이미지를 저장하고 관리합니다.

## 🎯 주요 기능
- **제품 데이터 저장**: 제품명, 가격, 설명, 사이즈, 재질 등 상세 정보
- **이미지 저장**: 제품 이미지를 BYTEA 형태로 바이너리 저장
- **스크래핑 작업 관리**: 스크래핑 작업의 상태 및 진행사항 추적
- **인덱싱 상태 관리**: 벡터 인덱싱 완료 여부 추적

## 🗄️ 데이터베이스 스키마

### products 테이블
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    source_global_url TEXT,         -- 영문 사이트 URL
    source_kr_url TEXT,             -- 한글 사이트 URL  
    product_name TEXT NOT NULL,     -- 제품명
    color TEXT,                     -- 색상
    price JSONB DEFAULT '{}',       -- {"global": "", "kr": ""}
    reward_points JSONB DEFAULT '{}', -- 리워드 포인트
    description JSONB DEFAULT '{}', -- 제품 설명
    material JSONB DEFAULT '{}',    -- 재질
    size JSONB DEFAULT '{}',        -- 사이즈
    issoldout BOOLEAN DEFAULT FALSE, -- 품절 여부
    indexed BOOLEAN DEFAULT FALSE,   -- 벡터DB 인덱싱 상태
    scraped_at TIMESTAMP DEFAULT NOW(),
    indexed_at TIMESTAMP
);
```

### product_images 테이블
```sql
CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,      -- 이미지 바이너리 저장
    image_order INTEGER DEFAULT 0  -- 이미지 순서
);
```

### scraping_jobs 테이블
```sql
CREATE TABLE scraping_jobs (
    id SERIAL PRIMARY KEY,
    target_url TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    products_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

## 🔧 설정 및 실행

### 환경변수
```bash
POSTGRES_HOST=uncommon_rag-postgres
POSTGRES_PORT=5434          # 외부 접근 포트
POSTGRES_INTERNAL_PORT=5432 # 컨테이너 내부 포트
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass2024!
```

### 실행 명령
```bash
# 데이터베이스 시작
cd PostgreSQLDB
source ../.env.global
docker compose up -d

# 상태 확인
docker compose ps
docker compose logs -f postgres
```

### 접속 정보
- **외부 접속**: `localhost:5434`
- **내부 접속**: `uncommon_rag-postgres:5432`
- **데이터베이스명**: `ragdb`
- **사용자**: `raguser`

## 📊 데이터 형식

### 입력 데이터 (products 테이블)
```json
{
    "product_name": "UNCOMMON Eyewear Model X",
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
        "global": "Premium eyewear with titanium frame",
        "kr": "티타늄 프레임의 프리미엄 아이웨어"
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
    "indexed": false
}
```

### 출력 데이터
- **SQL 쿼리 결과**: 표준 PostgreSQL 결과셋
- **JSON 형태**: 제품 정보를 JSON 객체로 반환
- **바이너리 데이터**: 이미지는 BYTEA로 저장/조회

## 🔄 통신 방식
- **프로토콜**: TCP/IP (PostgreSQL Wire Protocol)
- **연결**: SQLAlchemy ORM을 통한 비동기 연결
- **트랜잭션**: ACID 준수
- **인코딩**: UTF-8

## 🔗 의존성

### 필수 의존성
- **Docker & Docker Compose**: 컨테이너 실행 환경
- **PostgreSQL 16**: 메인 데이터베이스 엔진

### 연관 서비스
- **Scraper Service**: 데이터 생성 및 저장
- **Indexing Service**: 인덱싱 상태 업데이트
- **RAG API Service**: 제품 정보 조회

## 🚀 초기화 과정
1. Docker 컨테이너 시작
2. `init.sql` 스크립트 자동 실행
3. 테이블 및 인덱스 생성
4. 기본 데이터 설정 완료

## 🔍 모니터링
```bash
# 연결 상태 확인
docker exec -it uncommon_rag-postgres psql -U raguser -d ragdb -c "SELECT version();"

# 테이블 상태 확인
docker exec -it uncommon_rag-postgres psql -U raguser -d ragdb -c "SELECT COUNT(*) FROM products;"

# 로그 확인
docker compose logs postgres
```

## ⚠️ 주의사항
- **보안**: 현재 기본 인증 정보 사용 (운영 환경에서는 변경 필요)
- **백업**: 정기적인 데이터 백업 권장
- **성능**: 대용량 데이터 처리 시 인덱스 최적화 필요
- **포트**: 외부 포트 5434는 시스템 충돌 방지용