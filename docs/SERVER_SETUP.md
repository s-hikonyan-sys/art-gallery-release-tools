# サーバー初期セットアップガイド

> **このドキュメントについて**
> 本番サーバーを新規構築・再構築する際に必要な手動手順と、将来的な自動化 TODO をまとめたドキュメントです。

---

## TODO（将来対応）

> **将来的にはサーバー構築用の Ansible Playbook を用意する予定です。**
> 現時点では以下の手順を手動で実施してください。

---

## 前提条件

| 項目 | 内容 |
|---|---|
| OS | AlmaLinux 10 |
| デプロイディレクトリ | `/opt/art-gallery` |
| アプリケーションユーザー | `artgallery` |
| SSH 接続ユーザー | `ssh-admin`（admin_user） |
| Python | `/usr/bin/python3` が存在すること |

---

## 手順 1: 必須パッケージのインストール

以下のパッケージを手動でインストールしてください。

```bash
sudo dnf install -y \
  unzip \
  git \
  python3
```

### パッケージ一覧と用途

| パッケージ | 用途 |
|---|---|
| `unzip` | GitHub Actions の成果物（ZIP）を展開するために必要。**未インストールの場合、Frontend デプロイが失敗します。** |
| `git` | Backend コードのデプロイ（`git clone` / `git fetch`）に必要 |
| `python3` | Ansible の接続先として必要（`/usr/bin/python3`） |

---

## 手順 2: Docker Engine のインストール

```bash
# dnf-plugins-core のインストール
sudo dnf install -y dnf-plugins-core

# Docker GPG キーのインポート
sudo rpm --import https://download.docker.com/linux/centos/gpg

# Docker リポジトリの追加
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Docker Engine のインストール
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker サービスの起動と自動起動の有効化
sudo systemctl start docker
sudo systemctl enable docker
```

---

## 手順 3: ユーザー・グループの設定

```bash
# アプリケーション用システムユーザーの作成
sudo useradd -r -s /bin/bash -m -d /home/artgallery artgallery

# artgallery ユーザーを docker グループに追加
sudo usermod -aG docker artgallery

# ssh-admin ユーザーを docker グループに追加
sudo usermod -aG docker ssh-admin
```

---

## 手順 4: SSH セキュリティ設定

`/etc/ssh/sshd_config` を編集し、以下の設定を行ってください。

```
# root ログインを禁止
PermitRootLogin no

# パスワード認証を禁止（鍵認証のみ許可）
PasswordAuthentication no

# ログイン許可ユーザーを ssh-admin のみに限定
AllowUsers ssh-admin
```

設定後、sshd を再起動してください。

```bash
sudo systemctl restart sshd
```

> **注意**: `AllowUsers` に `artgallery` を含めないことで、アプリケーションユーザーによる SSH ログインを禁止しています。

---

## 手順 5: デプロイディレクトリの作成

```bash
sudo mkdir -p /opt/art-gallery/{src,dist,conf,logs,tmp,scripts}
sudo chown -R artgallery:artgallery /opt/art-gallery
```

---

## 手順 6: SSL 証明書の取得（Let's Encrypt）

### 前提

- ドメインの DNS A レコードがサーバーの IP アドレスに向いていること
- ポート 80・443 がファイアウォールで開放されていること
- アプリケーションが HTTP で起動済みであること

### Certbot のインストールと証明書取得

```bash
# Certbot のインストール
sudo dnf install -y certbot python3-certbot-nginx

# SSL 証明書の取得（ドメイン名は実際のドメインに置き換えてください）
sudo certbot --nginx -d <your-domain>
```

Certbot は以下を自動で行います。

1. SSL 証明書の取得
2. Nginx 設定への SSL 設定の追加
3. HTTP → HTTPS リダイレクトの設定

### 自動更新の確認

```bash
# 自動更新のテスト
sudo certbot renew --dry-run

# 自動更新タイマーの状態確認
systemctl status certbot.timer
```

### 証明書のパス

| ファイル | パス |
|---|---|
| 証明書 | `/etc/letsencrypt/live/<your-domain>/fullchain.pem` |
| 秘密鍵 | `/etc/letsencrypt/live/<your-domain>/privkey.pem` |

---

## 手順 7: systemd 自動起動サービスの登録

サーバー再起動時にアプリケーションが自動起動するよう、systemd サービスを登録します。
これは Ansible Playbook（`playbook_setup_startup_service.yml`）で自動化されています。

```bash
cd ansible
ansible-playbook playbook_setup_startup_service.yml \
  --inventory inventory/production.yml \
  --extra-vars "@/path/to/vars.json" \
  --tags "setup-startup-service"
```

---

## チェックリスト（新規構築時）

- [ ] `unzip` インストール済み
- [ ] `git` インストール済み
- [ ] `python3` インストール済み（`/usr/bin/python3`）
- [ ] Docker Engine インストール済み・起動済み
- [ ] `artgallery` ユーザー作成済み・docker グループ追加済み
- [ ] `ssh-admin` ユーザー docker グループ追加済み
- [ ] SSH セキュリティ設定済み（root ログイン禁止、パスワード認証禁止）
- [ ] デプロイディレクトリ（`/opt/art-gallery`）作成済み
- [ ] SSL 証明書取得済み（Let's Encrypt）
- [ ] systemd 自動起動サービス登録済み
