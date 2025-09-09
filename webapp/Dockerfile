FROM nginx:alpine

# Copy all HTML files to nginx default location
COPY *.html /usr/share/nginx/html/

# nginx 기본 설정 사용 (80 포트)
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]