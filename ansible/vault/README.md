# Vault設定ディレクトリ

このディレクトリには、Ansible Vaultで暗号化された設定ファイルを配置します。

**重要**: このディレクトリは**リリース作業用**です。本番環境に永続的に配置しないでください。

## ファイル構成

- `vault-config.yaml.vault.dev`: 開発環境・ローカル検証用設定ファイル（**Git管理対象外**）
  - Ansible Vaultで暗号化されたDBパスワードおよびシークレットキーを含む
  - `.gitignore`で除外されている
  - 手動で作成する必要がある

- `vault-config.yaml.vault.prod`: 本番環境用設定ファイル（**Git管理対象外**）
  - Ansible Vaultで暗号化されたDBパスワードおよびシークレットキーを含む
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
# secret_key: dev-secret-key-here

# 本番環境用（実際にはGitHub Actionsで行われるため不要）
ansible-vault create vault/vault-config.yaml.vault.prod --vault-password-file .vault_pass
# エディタで以下を記述：
# database:
#   password: prod-database-password-here
# secret_key: prod-secret-key-here
```

### 設定ファイルの編集

   ```bash
cd ansible

# 開発環境・ローカル検証用を編集
ansible-vault edit vault/vault-config.yaml.vault.dev --vault-password-file .vault_pass

# 本番環境用を編集（実際にはGitHub Actionsで行われるため不要）
ansible-vault edit vault/vault-config.yaml.vault.prod --vault-password-file .vault_pass
```

## パスワードの流れと具体的な処理フロー (Ephemeral Secrets Flow)

デプロイ時（特に GitHub Actions 環境）において、機密情報は以下の多段プロセスを経て安全に処理されます。これにより、平文パスワードがディスクに残ることを防ぎ、システム稼働中も最小限の権限と時間でのみ管理されます。

### 1. Vaultファイルの動的生成 (GitHub Actions)
- GitHub Actions の `setup-ansible-vault` カスタムアクションが起動します。
- GitHub Secrets に保存されている平文のパスワードやキー（`PROD_DB_PASSWORD_PLAINTEXT` 等）を取得します。
- これを `ansible-vault` で暗号化し、実行環境内の一時ディレクトリに **Ansible Vault 形式** のファイル `ansible/vault/vault-config.yaml.vault.prod` を作成します。

### 2. Fernet形式への再暗号化 (Ansible ブリッジ処理)
- Ansible の `secrets` ロールから `ansible/scripts/encrypt_secrets.py` が呼び出されます。
- このスクリプトは、一時的な Vault ファイルを復号して平文パスワードと暗号化キー (`secret_key`) を抽出後、Fernet 形式で再暗号化します。
- 最終的に、Secrets API コンテナのみが解読可能な `secrets.yaml.encrypted` ファイルが生成されます。

### 3. リモートサーバーへの配置
- 生成された `secrets.yaml.encrypted` が、Secrets API コンテナ用のパス（例: `/opt/art-gallery/conf/secrets/config/`）へコピーされます。
- このファイルは Backend や Database コンテナには**配置されません**（権限の分離）。
- ファイル権限は `0600`（所有者のみ読み書き可）に厳格に制限されます。

### 4. アプリケーション実行時の復号と認証 (ワンタイムトークン)
- **Secrets API 起動とトークン生成**:
    - `art-gallery-secrets-api` コンテナが最初に起動し、`secrets.yaml.encrypted` を復号してメモリ内に保持します。
    - 起動直後に、共有ボリュームへ専用のワンタイムトークン（`database_token.txt`, `backend_token.txt` / 権限 `0600`）を生成します。
- **PostgreSQL / Backend の起動待機**:
    - DBおよびBackendコンテナは、トークンファイルが生成されるまで起動を待機します（リトライ機構付き）。
- **認証とパスワード取得**:
    - 各コンテナがトークンを読み取り、`secrets-api` のエンドポイント（`/secrets/database/password`）へ `Authorization: Bearer <token>` を用いてリクエストを送ります。
    - 取得したパスワードをメモリ/環境変数にセットして、アプリケーションを安全に開始します。
- **セキュリティの最大化 (自動停止)**:
    - `secrets-api` はレスポンスを返した直後に、使用されたトークンファイルを**即座に物理削除**し、リプレイアタックを遮断します。
    - すべての配布が完了するか、起動から5分経過すると、**コンテナ自身が自動停止（自爆）**し、攻撃表面を完全に無くします。

## セキュリティ注意事項

- **設定ファイル**: `vault-config.yaml.vault.*`はGit管理対象外です（`.gitignore`で除外）。
- **プレーンテキストファイルを作成しない**: `vault-config.yaml`（プレーンテキスト）は作成しません。
- **コマンドライン引数や環境変数でパスワードを渡さない**: shellの履歴（history）に残るリスクを回避するためです。

## 本番環境での注意

`art-gallery-release-tools/`ディレクトリは**リリース作業用**です：
- **本番環境に永続的に配置しないでください。**
- リリース作業時に一時的に使用するのみです。
- Ansibleが自動的に一時的に配置し、使用後に自動削除します。
- 設定ファイル（`vault-config.yaml.vault.*`）は本番環境に永続的に残りません。

## GitHub Actions での使用

本番環境へのデプロイ時は、GitHub Actions の `setup-ansible-vault` カスタムアクションが、GitHub Secrets から取得した平文情報を使用して `vault-config.yaml.vault.prod` を一時的に生成します。このファイルは GitHub Actions の実行環境内でのみ存在し、実行終了後に自動的に破棄されます。