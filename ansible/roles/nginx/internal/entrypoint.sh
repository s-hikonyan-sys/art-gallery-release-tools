#!/bin/sh
set -e

# 他のコンテナのIPアドレスを取得して/etc/hostsに追加
# Docker ComposeではDNS解決が機能しない場合があるため、/etc/hostsを使用

BACKEND_IP=$(getent hosts art-gallery-api | awk '{print $1}' || echo "")
if [ -z "$BACKEND_IP" ]; then
    BACKEND_IP=$(docker inspect art-gallery-api --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null || echo "")
fi

if [ -n "$BACKEND_IP" ]; then
    if ! grep -q "backend" /etc/hosts; then
        echo "$BACKEND_IP backend art-gallery-api" >> /etc/hosts
    fi
fi

# WAF: compose で :ro マウントされたホスト側テンプレ出力を、起動時に実体パスへコピー
# （ディレクトリ未マウント・ファイル欠落時はスキップし Nginx のみ起動）
WAF_PREFIX="/opt/jp-secure/siteguardlite"
OVERLAY="${WAF_HOST_OVERLAY_DIR:-/tmp/host_waf_config}"
CONF_NAME="${WAF_DBUPDATE_CONF_NAME:-dbupdate.conf}"
# Nginx モジュールが読む本体は siteguardlite.ini（waf.ini はエイリアス用シンボリックリンク）
MAIN_INI="${WAF_MAIN_CONF_NAME:-siteguardlite.ini}"

if [ -d "$OVERLAY" ]; then
    if [ -f "$OVERLAY/$MAIN_INI" ]; then
        mkdir -p "$WAF_PREFIX/conf"
        cp -f "$OVERLAY/$MAIN_INI" "$WAF_PREFIX/conf/$MAIN_INI"
        chmod 600 "$WAF_PREFIX/conf/$MAIN_INI"
    fi
    if [ -f "$OVERLAY/$CONF_NAME" ]; then
        mkdir -p "$WAF_PREFIX/conf"
        cp -f "$OVERLAY/$CONF_NAME" "$WAF_PREFIX/conf/$CONF_NAME"
        chmod 600 "$WAF_PREFIX/conf/$CONF_NAME"
    fi
    if [ -f "$OVERLAY/dbupdate_waf" ]; then
        cp -f "$OVERLAY/dbupdate_waf" "$WAF_PREFIX/dbupdate_waf"
        chmod 755 "$WAF_PREFIX/dbupdate_waf"
    fi
fi

exec nginx -g "daemon off;"
