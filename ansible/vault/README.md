# Vault設定ディレクトリ

このディレクトリには、Ansible Vaultで暗号化された設定ファイルを配置します。

**重要**: このディレクトリは**リリース作業用**です。本番環境に永続的に配置しないでください。

## ファイル構成

- `vault-config.yaml.vault.dev`: 開発環境・ローカル検証用設定ファイル（**Git管理対象外**）
  - Ansible Vaultで暗号化されたDBパスワードを含む
  - `.gitignore`で除外されている
  - 手動で作成する必要がある

- `vault-config.yaml.vault.prod`: 本番環境用設定ファイル（**Git管理対象外**）
  - Ansible Vaultで暗号化されたDBパスワードを含む
  - `.gitignore`で除外されている
  - 手動で作成する必要がある

- `vault-config.yaml.vault.*.example`: 設定ファイルのテンプレート（Ansible Vault形式）
  - Git管理対象
  - このファイルを参考に`vault-config.yaml.vault.*`を作成

## 使用方法

### 設定ファイルの作成

   ```bash
cd ansible

# 開発環境・ローカル検証用
ansible-vault create vault/vault-config.yaml.vault.dev --vault-password-file .vault_pass
# エディタで以下を記述：
# database:
#   password: dev-database-password-here

# 本番環境用
ansible-vault create vault/vault-config.yaml.vault.prod --vault-password-file .vault_pass
# エディタで以下を記述：
# database:
#   password: prod-database-password-here
```

### 設定ファイルの編集

   ```bash
cd ansible

# 開発環境・ローカル検証用を編集
ansible-vault edit vault/vault-config.yaml.vault.dev --vault-password-file .vault_pass

# 本番環境用を編集
ansible-vault edit vault/vault-config.yaml.vault.prod --vault-password-file .vault_pass
```

## パスワードの流れと具体的な処理フロー

デプロイ時（特に GitHub Actions 環境）において、機密情報は以下の多段プロセスを経て安全に処理されます。これにより、リポジトリ内には暗号化された情報のみが保持され、サーバー上でも最小限の権限で管理されます。

### 1. Vaultファイルの動的生成 (GitHub Actions)
- GitHub Actions の `setup-ansible-vault` カスタムアクションが起動します。
- GitHub Secrets に保存されている平文のパスワード（`PROD_DB_PASSWORD_PLAINTEXT` 等）を取得します。
- これを `ansible-vault` で暗号化し、実行環境内の一時ディレクトリに **Ansible Vault 形式** のファイル `ansible/vault/vault-config.yaml.vault.prod` を作成します。

### 2. Fernet形式への再暗号化 (Ansible ブリッジ処理)
- Ansible の `vault.yml` タスクから `ansible/scripts/encrypt_secrets.py` が呼び出されます。
- このスクリプトは、上記の一時的な Vault ファイルを `ansible-vault` コマンドで復号し、平文のパスワードと暗号化キー (`secret_key`) を抽出します。
- **重要**: この際、`art-gallery-backend` リポジトリ内の `config/secrets.py` (`SecretManager` クラス) を動的にロードします。
- 抽出した `secret_key` を使用して、パスワードを **Fernet 形式** で再暗号化します。
- 最終的に、アプリケーションが直接解読可能な `secrets.yaml.encrypted` ファイルが生成されます。

### 3. リモートサーバーへの配置
- 生成された `secrets.yaml.encrypted` が、サーバーのパス（例: `/opt/art-gallery/conf/backend/config/`）へコピーされます。
- 併せて、復号ロジックを持つ `secrets.py` も `art-gallery-backend` リポジトリから配置されます。
- ファイル権限は `0600`（所有者のみ読み書き可）に厳格に制限されます。

### 4. アプリケーション実行時の復号
- **Secrets API コンテナ起動時**:
    - `art-gallery-secrets-api` コンテナが起動し、`Config` クラスを通じて `secrets.yaml.encrypted` を復号してメモリ内に保持します。
- **PostgreSQL 起動時**: 
    - `postgres-entrypoint.sh` が起動し、`secrets-api` のエンドポイント（`/secrets/database/password`）にリクエストを送ります。
    - 取得したパスワードを `POSTGRES_PASSWORD` 環境変数にセットして DB を開始します。
- **Backend アプリ起動時**: 
    - `config/__init__.py` の初期化プロセスで `secrets-api` にリクエストを送り、データベースパスワードを取得します。
    - 平文パスワードがディスク上に永続化されることはありません。
- **セキュリティの最大化**:
    - `secrets-api` はレスポンスを返した直後に、認証用トークンファイル（`auth_token.txt`）を自ら削除し、以後の不正リクエストを遮断します。


## セキュリティ注意事項

- **設定ファイル**: `vault-config.yaml.vault.*`はGit管理対象外です（`.gitignore`で除外）
- **プレーンテキストファイルを作成しない**: `vault-config.yaml`（プレーンテキスト）は作成しません
- **コマンドライン引数や環境変数でパスワードを渡さない**: historyに残る可能性があるため

## 本番環境での注意

`art-gallery-release-tools/`ディレクトリは**リリース作業用**です：
- **本番環境に永続的に配置しないでください**
- リリース作業時に一時的に使用するのみです
- Ansibleが自動的に一時的に配置し、使用後に自動削除します
- 設定ファイル（`vault-config.yaml.vault.*`）は本番環境に永続的に残りません

## GitHub Actions での使用

本番環境へのデプロイ時は、GitHub Actions の `setup-ansible-vault` カスタムアクションが、GitHub Secrets から取得した平文パスワードを使用して `vault-config.yaml.vault.prod` を一時的に生成します。このファイルは GitHub Actions の実行環境内でのみ存在し、実行終了後に自動的に破棄されます。
