#!/bin/sh
set -e

# 他のコンテナのIPアドレスを取得して/etc/hostsに追加
# Docker ComposeではDNS解決が機能しない場合があるため、/etc/hostsを使用

# backendコンテナのIPアドレスを取得
BACKEND_IP=$(getent hosts art-gallery-api | awk '{print $1}' || echo "")
if [ -z "$BACKEND_IP" ]; then
    # コンテナ名で解決できない場合、ネットワークから取得を試みる
    BACKEND_IP=$(docker inspect art-gallery-api --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || echo "")
fi

# /etc/hostsに追加（重複チェック）
if [ -n "$BACKEND_IP" ]; then
    if ! grep -q "backend" /etc/hosts; then
        echo "$BACKEND_IP backend art-gallery-api" >> /etc/hosts
    fi
fi

# Nginxを起動
exec nginx -g "daemon off;"
