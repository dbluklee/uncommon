FROM nginx:alpine

# Copy all HTML files to nginx default location
COPY *.html /usr/share/nginx/html/

# Copy custom nginx configuration if needed
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]