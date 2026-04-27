# SiteGuard Server Edition 運用ガイド

本ドキュメントは **art-gallery** プロジェクトにおける SiteGuard Server Edition (Nginx版) の
セットアップ・バージョン管理・日常オペレーション手順を記載します。

---

## 1. 概要

### 採用方針
- **2層イメージ戦略**: SiteGuard をコンパイルする重いビルドはベースイメージ(`nginx-siteguard-base`)に隔離し、アプリ層(`art-gallery-nginx`)は `entrypoint.sh` を追加するのみ。
- **全ビルドは GitHub Actions 上で実行**: VPS 上でのイメージビルドは行わない。
- **SiteGuard パッケージは GitHub Release に保管**: さくらのVPS経由でのみダウンロード可能なため、初回に VPS を中継して GitHub Release へ格納する。
- **ローカル開発環境は影響なし**: `nginx.dev.conf` は SiteGuard なしで動作する。

### ライセンス
- さくらのVPS利用者向け無償提供（株式会社EGセキュアソリューションズ）
- ライセンス情報は GitHub Actions Secrets で管理（`SITEGUARD_SERIAL_KEY`, `SITEGUARD_SUPPORT_ID`, `SITEGUARD_PASSWORD`）

---

## 2. イメージ構成

```
nginx-siteguard-base:{v{nginx_version}-sg{siteguard_version}}
│  Ubuntu 22.04
│  nginx (ソースビルド + SiteGuard モジュール静的リンク)
│  /opt/jp-secure/siteguardlite/
│
└── art-gallery-nginx:{v{release_version}}
      entrypoint.sh を追加
      (SiteGuard 設定・シグネチャは Docker Volume で永続化)
```

### バージョン形式

| イメージ | 形式 | 例 |
|:---|:---|:---|
| `nginx-siteguard-base` | `v{nginx_version}-sg{siteguard_version}` | `v1.26.3-sg8.00-3` |
| `art-gallery-nginx` | `v{release_version}` | `v1.0.0` |

---

## 3. 初回セットアップ手順

### Step 1: SiteGuard パッケージを GitHub Release へ格納

```
GitHub Actions → setup_siteguard_package.yml → workflow_dispatch
  Input: siteguard_version = 8.00-3
```

実行すると:
1. VPS 上で SiteGuard インストーラーをダウンロード
2. GitHub Actions ランナーへ転送（SCP）
3. GitHub Release `siteguard-packages` にアップロード

### Step 2: ベースイメージをビルド

```
GitHub Actions → build_nginx_base.yml → workflow_dispatch
  Input:
    release_version = v1.26.3-sg8.00-3
    nginx_version   = 1.26.3
    siteguard_version = 8.00-3
```

実行すると:
1. GitHub Release から SiteGuard パッケージをダウンロード
2. Ubuntu 22.04 + nginx ソースビルド + SiteGuard モジュール組み込み
3. GHCR へ `nginx-siteguard-base:v1.26.3-sg8.00-3` をプッシュ
4. `manifest/nginx/base/nginx_base_version_manifest.yml` 更新 PR を作成

### Step 3: アプリイメージをビルド

```
GitHub Actions → build_nginx.yml → workflow_dispatch
  Input:
    release_version = v1.0.0
    base_version    = v1.26.3-sg8.00-3
```

実行すると:
1. `nginx-siteguard-base:v1.26.3-sg8.00-3` をベースに `entrypoint.sh` を追加
2. GHCR へ `art-gallery-nginx:v1.0.0` をプッシュ
3. `manifest/nginx/image/nginx_version_manifest.yml` 更新 PR を作成

### Step 4: デプロイ（イメージ更新）

```
GitHub Actions → deploy_nginx.yml → workflow_dispatch
  Input:
    release_version  = v1.0.0
    run_deploy_image = true
```

### Step 5: SiteGuard 初期設定（初回のみ）

nginx コンテナが起動した後に **一度だけ** 実行する。

```
GitHub Actions → deploy_nginx.yml → workflow_dispatch
  Input:
    run_setup_siteguard = true
    ※ Secrets: SITEGUARD_SERIAL_KEY, SITEGUARD_SUPPORT_ID, SITEGUARD_PASSWORD
```

内容:
1. シグネチャ更新 URL をさくらのVPS専用 URL に変更
2. ライセンス情報を設定ファイルへ書き込み
3. 設定適用 (`make reconfig`)
4. 初回シグネチャ更新

---

## 4. 日常オペレーション

### シグネチャ更新（定期メンテナンス）

```
GitHub Actions → update_siteguard_signatures.yml → workflow_dispatch
```

または `deploy_nginx.yml` の `update-siteguard-signatures` タグで実行。

### nginx.conf への SiteGuard 設定追加

`art-gallery-nginx/nginx.conf` に以下を追加してください:

```nginx
# SiteGuard WAF設定
include /opt/jp-secure/siteguardlite/nginx/siteguardlite.conf;
```

> ローカル開発用の `nginx.dev.conf` には追加しない（SiteGuard 不要）。

---

## 5. バージョンアップ手順

### SiteGuard バージョンアップ

1. `setup_siteguard_package.yml` で新バージョンパッケージを GitHub Release へ格納
2. `build_nginx_base.yml` で新タグ（例: `v1.26.3-sg8.00-4`）でベースイメージをビルド
3. `build_nginx.yml` で新ベースバージョンを指定してアプリイメージをビルド
4. `deploy_nginx.yml` でデプロイ

### nginx バージョンアップ

1. `build_nginx_base.yml` で新タグ（例: `v1.27.0-sg8.00-3`）でベースイメージをビルド
2. 以降は SiteGuard バージョンアップと同様

---

## 6. Docker Volumes

| ボリューム名 | マウント先 | 内容 |
|:---|:---|:---|
| `art-gallery_siteguard_conf` | `/opt/jp-secure/siteguardlite/conf` | SiteGuard 設定・ライセンス・更新URL |
| `art-gallery_siteguard_sig` | `/opt/jp-secure/siteguardlite/ngx_waf_data` | WAF シグネチャファイル |

コンテナを再作成しても設定・シグネチャは保持されます。

---

## 7. GitHub Actions Secrets / Variables 一覧

| 名前 | 種別 | 内容 |
|:---|:---:|:---|
| `SITEGUARD_SERIAL_KEY` | Secret | SiteGuard シリアルキー |
| `SITEGUARD_SUPPORT_ID` | Secret | サポートID（シグネチャ更新認証に使用）|
| `SITEGUARD_PASSWORD` | Secret | サポートパスワード（シグネチャ更新認証に使用）|
| `PROD_HOST` | Variable | 本番サーバーホスト名/IP |
| `PROD_SSH_USER` | Variable | SSH ユーザー |
| `PROD_SSH_PRIVATE_KEY` | Secret | SSH 秘密鍵 |
| `PROD_SSH_KNOWN_HOSTS` | Secret | SSH known_hosts |

---

## 8. トラブルシューティング

### SiteGuard モジュールが読み込まれない

```bash
docker exec art-gallery-nginx nginx -t
```

エラーに `siteguardlite.conf` が含まれる場合: `nginx.conf` に include 設定が不足している。

### シグネチャ更新が失敗する

1. `SITEGUARD_SUPPORT_ID` / `SITEGUARD_PASSWORD` の設定を確認
2. VPS から `www.jp-secure.com` への HTTP アクセスを確認
3. ボリューム `art-gallery_siteguard_conf` 内の `dbupdate_waf_url.conf` の URL を確認

### ベースイメージビルドが失敗する

- GitHub Release `siteguard-packages` にパッケージが存在するか確認
- `nginx_version` が `nginx.org` で公開されているバージョンか確認
