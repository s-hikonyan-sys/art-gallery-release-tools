# art-gallery-nginx Dockerfile（アプリ層）
# nginx-siteguard-base をベースに entrypoint.sh を追加するのみ。
# SiteGuard 本体は nginx-siteguard-base に含まれるため、このイメージは軽量かつ高速にビルドできる。
#
# BASE_VERSION 形式: v{nginx_version}-sg{siteguard_version} (例: v1.26.3-sg8.00-3)
# イメージタグ形式: v{release_version} (例: v1.0.0)

ARG BASE_VERSION
FROM ghcr.io/s-hikonyan-sys/nginx-siteguard-base:${BASE_VERSION}

# entrypoint をイメージに含める
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
