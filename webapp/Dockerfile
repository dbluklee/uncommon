FROM nginx:alpine

# envsubst 명령어를 위한 패키지 설치
RUN apk add --no-cache gettext

# Copy all HTML files to nginx default location
COPY *.html /usr/share/nginx/html/

# Copy nginx template and entrypoint script
COPY nginx.conf.template /nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE ${WEBAPP_INTERNAL_PORT}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]