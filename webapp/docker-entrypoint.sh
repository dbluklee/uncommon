#!/bin/bash
set -e

# 환경변수 확인 (기본값 없음 - 누락 시 에러 발생)
export WEBAPP_INTERNAL_PORT=${WEBAPP_INTERNAL_PORT}
export RAG_API_HOST=${RAG_API_HOST}
export RAG_API_INTERNAL_PORT=${RAG_API_INTERNAL_PORT}

# nginx 설정 파일 생성
envsubst '${WEBAPP_INTERNAL_PORT} ${RAG_API_HOST} ${RAG_API_INTERNAL_PORT}' < /nginx.conf.template > /etc/nginx/conf.d/default.conf

# HTML 파일들의 하드코딩된 포트 번호를 환경변수로 대체
# 8003, 8013 등을 실제 RAG_API_PORT로 변경
find /usr/share/nginx/html -name "*.html" -exec sed -i "s/:8003/:${RAG_API_PORT}/g" {} \;
find /usr/share/nginx/html -name "*.html" -exec sed -i "s/:8013/:${RAG_API_PORT}/g" {} \;

# nginx 실행
exec "$@"