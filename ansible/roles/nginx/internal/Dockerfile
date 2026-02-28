FROM nginx:alpine

# ログディレクトリの作成
RUN mkdir -p /var/log/nginx

# entrypoint をイメージに含める
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
