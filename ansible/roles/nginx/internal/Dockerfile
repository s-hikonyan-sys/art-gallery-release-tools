# art-gallery-nginx Dockerfile（アプリ層）
# nginx-base をベースに entrypoint.sh を追加するのみの軽量かつ高速なビルド。
# ベースイメージはプライベートリポジトリ art-gallery-nginx-base でビルドされる。
#
# BASE_VERSION: ベースイメージのバージョン（art-gallery-nginx-base の build_nginx_base.yml で発行）
# イメージタグ形式: v{release_version} (例: v1.0.0)

ARG BASE_VERSION
FROM ghcr.io/s-hikonyan-sys/nginx-base:${BASE_VERSION}

# WAF: setup_waf / シグネチャ更新で make reconfig / make update をコンテナ内で実行するため
# nginx-base の runtime ステージには make が含まれない
RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# entrypoint をイメージに含める
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
