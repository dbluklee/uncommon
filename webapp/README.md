# Web App (웹 애플리케이션)

## 📋 개요
UNCOMMON RAG 시스템의 프론트엔드 웹 애플리케이션입니다. 모바일 최적화된 채팅 인터페이스와 관리자 대시보드를 제공하며, Nginx를 통해 정적 파일을 서빙합니다.

## 🎯 주요 기능
- **실시간 채팅**: Server-Sent Events 기반 스트리밍 대화
- **모바일 최적화**: 반응형 디자인으로 모든 디바이스 지원
- **이미지 업로드**: 멀티모달 채팅 지원
- **관리자 대시보드**: 시스템 상태 모니터링 및 제어
- **디버깅 도구**: 검색 결과 및 프롬프트 분석

## 🚀 실행 방법

### 환경변수
```bash
WEBAPP_PORT=3000                   # 외부 접근 포트
WEBAPP_INTERNAL_PORT=80           # 컨테이너 내부 포트 (Nginx)
RAG_API_HOST=uncommon_rag-api     # RAG API 서비스 호스트
RAG_API_PORT=8000                 # RAG API 내부 포트
```

### 실행 명령
```bash
# 웹 애플리케이션 시작
cd webapp
source ../.env.global
docker compose up -d

# 로컬 개발 (정적 파일 서버)
python -m http.server 3000
```

### 접속 정보
- **메인 채팅**: `http://localhost:3000`
- **관리자 대시보드**: `http://localhost:3000/admin.html`
- **디버깅 도구**: `http://localhost:3000/debug.html`

## 📱 페이지 구성

### 1. 메인 채팅 페이지 (`index.html`)
```html
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UNCOMMON AI Assistant</title>
</head>
<body>
    <div id="chat-container">
        <div id="messages"></div>
        <div id="input-container">
            <input type="text" id="user-input" placeholder="궁금한 제품을 물어보세요...">
            <input type="file" id="image-upload" accept="image/*">
            <button id="send-btn">전송</button>
        </div>
    </div>
</body>
</html>
```

**주요 기능:**
- 실시간 스트리밍 채팅
- 이미지 업로드 및 미리보기
- 모바일 터치 최적화
- 자동 스크롤 및 타이핑 애니메이션

### 2. 관리자 대시보드 (`admin.html`)
```html
<div id="admin-dashboard">
    <h1>UNCOMMON RAG 시스템 관리</h1>
    
    <section id="system-status">
        <h2>시스템 상태</h2>
        <div id="service-status"></div>
    </section>
    
    <section id="data-management">
        <h2>데이터 관리</h2>
        <button id="start-scraping">스크래핑 시작</button>
        <button id="start-indexing">인덱싱 시작</button>
    </section>
    
    <section id="statistics">
        <h2>통계</h2>
        <div id="stats-display"></div>
    </section>
</div>
```

**주요 기능:**
- 모든 서비스 상태 실시간 모니터링
- 스크래핑/인덱싱 작업 제어
- 시스템 통계 및 성능 지표
- 에러 로그 확인

### 3. 디버깅 도구 (`debug.html`)
```html
<div id="debug-panel">
    <h1>RAG 시스템 디버깅</h1>
    
    <section id="search-debug">
        <h2>검색 결과 분석</h2>
        <input type="text" id="debug-query" placeholder="검색 쿼리 입력">
        <button id="debug-search">검색 테스트</button>
        <div id="search-results"></div>
    </section>
    
    <section id="prompt-debug">
        <h2>프롬프트 분석</h2>
        <div id="prompt-display"></div>
    </section>
</div>
```

**주요 기능:**
- 벡터 검색 결과 상세 분석
- LLM 프롬프트 구성 확인
- 유사도 점수 및 컨텍스트 검증

## 💬 실시간 채팅 구현

### JavaScript 스트리밍 클라이언트
```javascript
class ChatClient {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.eventSource = null;
    }
    
    async sendMessage(message, imageFile = null) {
        const formData = new FormData();
        formData.append('query', message);
        formData.append('stream', 'true');
        
        if (imageFile) {
            formData.append('image', imageFile);
        }
        
        // 스트리밍 연결 시작
        this.setupEventStream(formData);
    }
    
    setupEventStream(formData) {
        const url = imageFile ? '/chat/multimodal' : '/chat';
        
        fetch(`${this.apiUrl}${url}`, {
            method: 'POST',
            body: formData
        }).then(response => {
            const reader = response.body.getReader();
            this.readStream(reader);
        });
    }
    
    async readStream(reader) {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    this.handleStreamData(data);
                }
            }
        }
    }
    
    handleStreamData(data) {
        switch (data.type) {
            case 'search_start':
                this.showSearchStatus('검색 중...');
                break;
            case 'search_results':
                this.displaySearchResults(data.products);
                break;
            case 'token':
                this.appendToResponse(data.content);
                break;
            case 'done':
                this.finishResponse();
                break;
        }
    }
}
```

### CSS 모바일 최적화
```css
/* 반응형 채팅 인터페이스 */
#chat-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-width: 800px;
    margin: 0 auto;
}

#messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    scroll-behavior: smooth;
}

.message {
    margin-bottom: 15px;
    padding: 12px 16px;
    border-radius: 18px;
    max-width: 80%;
    word-wrap: break-word;
}

.user-message {
    background: #007AFF;
    color: white;
    margin-left: auto;
    text-align: right;
}

.assistant-message {
    background: #F2F2F7;
    color: #000;
    margin-right: auto;
}

/* 모바일 최적화 */
@media (max-width: 768px) {
    #input-container {
        padding: 10px;
        position: sticky;
        bottom: 0;
        background: white;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    
    #user-input {
        font-size: 16px; /* iOS 줌 방지 */
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 25px;
        flex: 1;
    }
    
    .message {
        max-width: 90%;
        font-size: 14px;
    }
}
```

## 📊 입력/출력 데이터 형식

### 채팅 요청 (fetch)
```javascript
// 텍스트 전용 채팅
const textRequest = {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: "티타늄 안경테 추천해주세요",
        stream: true
    })
};

// 멀티모달 채팅 (이미지 포함)
const formData = new FormData();
formData.append('query', '이 안경과 비슷한 제품 추천해주세요');
formData.append('image', imageFile);
formData.append('stream', 'true');

const multiModalRequest = {
    method: 'POST',
    body: formData
};
```

### 스트리밍 응답 처리
```javascript
// Server-Sent Events 형태의 응답
const eventTypes = {
    'search_start': { message: "검색 중..." },
    'search_results': { count: 3, products: [...] },
    'generation_start': { message: "답변 생성 중..." },
    'token': { content: "추천", timestamp: "2024-01-10T10:30:00Z" },
    'done': { message: "답변 완료" },
    'error': { message: "오류 발생" }
};
```

### 관리자 API 호출
```javascript
// 시스템 상태 조회
async function getSystemStatus() {
    const services = ['scraper', 'indexing', 'rag-api'];
    const status = {};
    
    for (const service of services) {
        try {
            const response = await fetch(`http://localhost:800${services.indexOf(service)+1}/health`);
            status[service] = await response.json();
        } catch (error) {
            status[service] = { status: 'error', message: error.message };
        }
    }
    
    return status;
}

// 스크래핑 작업 시작
async function startScraping() {
    const response = await fetch('http://localhost:8001/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            target_url: 'https://ucmeyewear.earth/category/all/87/'
        })
    });
    
    return response.json();
}
```

## 🔄 통신 방식

### HTTP + Server-Sent Events
```javascript
// SSE 연결 설정
const eventSource = new EventSource(`${API_URL}/chat-stream`);

eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    handleIncomingMessage(data);
};

eventSource.onerror = function(event) {
    console.error('SSE connection error:', event);
    // 재연결 로직
    setTimeout(() => {
        eventSource.close();
        setupNewConnection();
    }, 5000);
};
```

### Fetch API with Streaming
```javascript
// 스트리밍 응답 처리
async function streamingFetch(url, options) {
    const response = await fetch(url, options);
    const reader = response.body.getReader();
    
    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            // 청크 데이터 처리
            const chunk = new TextDecoder().decode(value);
            processStreamChunk(chunk);
        }
    } finally {
        reader.releaseLock();
    }
}
```

### WebSocket (미래 확장)
```javascript
// WebSocket 연결 (현재는 미구현)
class WebSocketClient {
    constructor(url) {
        this.ws = new WebSocket(url);
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.ws.onopen = () => console.log('WebSocket connected');
        this.ws.onmessage = (event) => this.handleMessage(JSON.parse(event.data));
        this.ws.onerror = (error) => console.error('WebSocket error:', error);
        this.ws.onclose = () => this.reconnect();
    }
}
```

## 🔗 의존성

### 프론트엔드 기술 스택
- **Vanilla JavaScript**: 프레임워크 없는 순수 자바스크립트
- **HTML5**: 시맨틱 마크업 및 모던 웹 표준
- **CSS3**: Flexbox, Grid, 반응형 디자인
- **Server-Sent Events**: 실시간 스트리밍 통신

### 외부 라이브러리 (CDN)
```html
<!-- 아이콘 폰트 -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

<!-- 마크다운 렌더링 -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<!-- 코드 하이라이팅 -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/themes/prism.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.24.1/prism.min.js"></script>
```

### 서버 의존성
- **Nginx**: 정적 파일 서빙 및 프록시
- **RAG API Service**: 채팅 및 검색 기능
- **관리 API들**: 스크래핑, 인덱싱 서비스

## 🎨 UI/UX 특징

### 모바일 최적화
```css
/* 터치 친화적 버튼 */
button {
    min-height: 44px;  /* iOS 권장 터치 영역 */
    min-width: 44px;
    touch-action: manipulation;
}

/* 스크롤 최적화 */
#messages {
    -webkit-overflow-scrolling: touch;  /* iOS 부드러운 스크롤 */
    overscroll-behavior: contain;       /* 바운스 방지 */
}

/* 입력 영역 고정 */
#input-container {
    position: sticky;
    bottom: 0;
    background: white;
    z-index: 1000;
}
```

### 다크 모드 지원
```css
@media (prefers-color-scheme: dark) {
    body {
        background-color: #1c1c1e;
        color: #ffffff;
    }
    
    .assistant-message {
        background: #2c2c2e;
        color: #ffffff;
    }
    
    #input-container {
        background: #1c1c1e;
        border-top: 1px solid #3a3a3c;
    }
}
```

### 접근성 (Accessibility)
```html
<!-- ARIA 레이블 및 역할 -->
<div id="messages" role="log" aria-live="polite" aria-label="채팅 메시지">
<input type="text" id="user-input" 
       aria-label="메시지 입력" 
       placeholder="궁금한 제품을 물어보세요...">
<button id="send-btn" aria-label="메시지 전송">
    <i class="fas fa-paper-plane" aria-hidden="true"></i>
</button>

<!-- 키보드 네비게이션 -->
<script>
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && e.target.id === 'user-input') {
        sendMessage();
    }
    if (e.key === 'Escape') {
        closeModal();
    }
});
</script>
```

## 📈 성능 최적화

### 이미지 최적화
```javascript
// 이미지 압축 및 리사이징
function compressImage(file, maxWidth = 800, quality = 0.8) {
    return new Promise(resolve => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
            const ratio = Math.min(maxWidth / img.width, maxWidth / img.height);
            canvas.width = img.width * ratio;
            canvas.height = img.height * ratio;
            
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(resolve, 'image/jpeg', quality);
        };
        
        img.src = URL.createObjectURL(file);
    });
}
```

### 지연 로딩
```javascript
// 채팅 히스토리 지연 로딩
const observerOptions = {
    root: document.getElementById('messages'),
    rootMargin: '50px',
    threshold: 0.1
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadMoreMessages();
        }
    });
}, observerOptions);
```

### 메모리 관리
```javascript
// EventSource 정리
function cleanup() {
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    
    // 이미지 URL 해제
    document.querySelectorAll('img[data-object-url]').forEach(img => {
        URL.revokeObjectURL(img.src);
    });
}

window.addEventListener('beforeunload', cleanup);
```

## 🔍 디버깅 도구

### 콘솔 로깅
```javascript
class DebugLogger {
    static log(category, message, data = null) {
        if (window.DEBUG_MODE) {
            console.group(`🔍 ${category}`);
            console.log(message);
            if (data) console.table(data);
            console.groupEnd();
        }
    }
    
    static error(category, error) {
        console.error(`❌ ${category}:`, error);
        // 에러 리포팅 서비스 연동 가능
    }
}

// 사용 예시
DebugLogger.log('CHAT', 'Message sent', { query: userInput, timestamp: Date.now() });
```

### 성능 모니터링
```javascript
// 응답 시간 측정
class PerformanceMonitor {
    static measureChatResponse(startTime) {
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        console.log(`⏱️ Chat Response Time: ${duration.toFixed(2)}ms`);
        
        // 통계 수집
        this.updateStats('chat_response_time', duration);
    }
    
    static updateStats(metric, value) {
        const stats = JSON.parse(localStorage.getItem('performance_stats') || '{}');
        if (!stats[metric]) stats[metric] = [];
        
        stats[metric].push({ value, timestamp: Date.now() });
        
        // 최근 100개만 유지
        if (stats[metric].length > 100) {
            stats[metric] = stats[metric].slice(-100);
        }
        
        localStorage.setItem('performance_stats', JSON.stringify(stats));
    }
}
```

## ⚠️ 주의사항
- **브라우저 호환성**: 모던 브라우저 (ES6+, Fetch API) 필요
- **네트워크 오류**: SSE 연결 끊김 시 재연결 로직 중요
- **메모리 누수**: EventSource 및 이미지 객체 정리 필수
- **모바일 성능**: 큰 이미지 파일 압축 처리 권장
- **보안**: XSS 방지를 위한 사용자 입력 검증 및 이스케이프 처리