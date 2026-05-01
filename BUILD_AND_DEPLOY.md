# ビルド・デプロイとバージョン管理

このドキュメントは、`art-gallery-release-tools` における **ビルド／デプロイの手順**と、**どのファイルがバージョン・成果物とどう紐づくか**をまとめたものです。詳細な全体像は [README.md](README.md) を参照してください。

**前提（初回のみ）**: マニフェスト更新やデプロイ記録の PR を Actions で自動作成するには、[GitHub リポジトリ設定（Actions / PR 前提）](docs/GITHUB_REPOSITORY_SETUP.md) のとおり、リポジトリで **Read and write** および **Allow GitHub Actions to create and approve pull requests** を有効にしてください。

## 1. 方針の要約

- **手動デプロイ**: 各ワークフローは原則 `workflow_dispatch` で実行します。
- **マニフェストの役割**: Git タグに依存せず、release-tools 上の YAML で **イメージタグ ↔ ソースコミット ↔ ビルド記録** を追跡できるようにします。
- **配置**: マニフェストはリポジトリルートではなく **`manifest/<サービス>/<種別>/`** に置きます（`image` / `code` / `deploy` など）。ルートの散在と PR の衝突を減らすためです。
- **インデックス**: 各ファイルへのパスは **`manifest/version_index.yml`** にまとめています（人間・ツール向けの索引）。

```yaml
# manifest/version_index.yml（抜粋）
frontend_manifest_path: "manifest/frontend/image/frontend_version_manifest.yml"
backend_image_manifest_path: "manifest/backend/image/backend_version_manifest.yml"
backend_code_manifest_path: "manifest/backend/code/backend_code_manifest.yml"
backend_deploy_manifest_path: "manifest/backend/deploy/backend_deploy_manifest.yml"
database_image_manifest_path: "manifest/database/image/database_version_manifest.yml"
secrets_image_manifest_path: "manifest/secrets/image/secrets_version_manifest.yml"
secrets_code_manifest_path: "manifest/secrets/code/secrets_code_manifest.yml"
secrets_deploy_manifest_path: "manifest/secrets/deploy/secrets_deploy_manifest.yml"
nginx_image_manifest_path: "manifest/nginx/image/nginx_version_manifest.yml"
nginx_code_manifest_path: "manifest/nginx/code/nginx_code_manifest.yml"
nginx_deploy_manifest_path: "manifest/nginx/deploy/nginx_deploy_manifest.yml"
```

- **Database（SQL）**: **SQL の版管理を release-tools のマニフェストで二重に持たない**方針です。スキーマの正は **`art-gallery-database` のディレクトリ（例: `migrations/v…/`）と、実行後の DB 側 `schema_migrations`** です。release-tools に SQL 専用のマニフェストは置きません。

---

## 2. コンポーネント別の実装状況（○ / △ / ✗）

凡例: **○** 実装済み / **△** 一部（マニフェストや運用が Backend ほど集約されていない） / **✗** 未実装

| コンポーネント | ビルド用 WF | デプロイ用 WF | マニフェスト・トレーサビリティ |
|:---|:---:|:---:|:---|
| **Backend** | `build_backend.yml` | `deploy_backend.yml` | **○** `manifest/backend/image/backend_version_manifest.yml`（イメージ） / `manifest/backend/code/backend_code_manifest.yml`（コード版・`register_backend_code.yml` が更新） / `manifest/backend/deploy/backend_deploy_manifest.yml`（本番デプロイ履歴） |
| **Frontend** | `build_frontend.yml` | `deploy_frontend.yml` | **○** `manifest/frontend/image/frontend_version_manifest.yml`（ビルド記録・PR 更新）。デプロイは **GitHub Actions の Artifact**（`frontend-dist-<version>`）を名前で解決 |
| **Secrets API** | `build_secrets.yml` | `deploy_secrets.yml` | **○** `manifest/secrets/image/secrets_version_manifest.yml`（イメージ） / `manifest/secrets/code/secrets_code_manifest.yml`（コード版・`register_secrets_code.yml` が更新） / `manifest/secrets/deploy/secrets_deploy_manifest.yml`（本番デプロイ履歴） |
| **Database** | `build_database.yml` | `deploy_database.yml` | **○** `manifest/database/image/database_version_manifest.yml`（イメージ）。**SQL の版は DB リポジトリ＋`schema_migrations` が正**（下記「Database」） |
| **Nginx（ベース層）** | `build_nginx_base.yml`（Private リポジトリ） | — | **○** Private 側マニフェストで管理（release-tools 管轄外） |
| **Nginx（アプリ層）** | `build_nginx.yml` | `deploy_nginx.yml` / `reload_nginx.yml` | **○** `manifest/nginx/image/nginx_version_manifest.yml`（イメージ） / `manifest/nginx/code/nginx_code_manifest.yml`（コード版・`register_nginx_code.yml` が更新） / `manifest/nginx/deploy/nginx_deploy_manifest.yml`（本番デプロイ履歴） |

---

## 3. Backend

- **イメージビルド**: `build_backend.yml` → GHCR プッシュ後、`manifest/backend/image/backend_version_manifest.yml` 更新の PR。
- **コード版の登録**: `register_backend_code.yml` → `manifest/backend/code/backend_code_manifest.yml` 更新の PR。
- **デプロイ**: `deploy_backend.yml` の入力 `run_deploy_image` / `run_deploy_code`、`release_version`、`code_version`（任意）、`backend_ref` など。**イメージ更新時**は `release_version` が `manifest/backend/image/backend_version_manifest.yml` に存在する必要があります。
- **履歴**: デプロイ成功後に `manifest/backend/deploy/backend_deploy_manifest.yml` が追記されます。

詳細な表と推奨フローは [README.md の「Backend のバージョン管理」](README.md#backend-のバージョン管理マニフェスト) を参照してください。

---

## 4. Frontend（リポジトリと release-tools の役割分担）

| 場所 | 役割 |
|:---|:---|
| **art-gallery-frontend** | CI は **lint・テストまで**（本番ビルドや Artifact 登録・マニフェスト更新は行わない想定）。 |
| **art-gallery-release-tools** | **`build_frontend.yml`**: 別リポジトリをチェックアウト（トークン使用）→ lint / test / `npm run build` → **Artifact アップロード** → 共通アクション `create-build-manifest-pr` で `manifest/frontend/image/frontend_version_manifest.yml`（`artifact_name` 等）更新の PR。**`deploy_frontend.yml`**: 同じバージョン名の Artifact を取得してサーバーへ展開。 |

- フロントの **本番向けビルド・Artifact・マニフェスト** は release-tools に集約し、**機密トークンやマニフェストの更新権限**も release-tools 側のシークレット・ワークフローで管理する方針です。マニフェストには GHCR イメージではなく **Artifact 名**（`frontend-dist-<version>`）を記録します。
- デプロイ前に、対象 `release_version` で **`build_frontend.yml` が成功済み**であること（Artifact が残っていること）が必要です。

---

## 5. Secrets API

- **イメージビルド**: `build_secrets.yml` → GHCR プッシュ後、`manifest/secrets/image/secrets_version_manifest.yml` 更新の PR。
- **コード版の登録**: `register_secrets_code.yml` → `manifest/secrets/code/secrets_code_manifest.yml` 更新の PR。
- **デプロイ**: `deploy_secrets.yml` の入力 `run_deploy_image` / `run_deploy_code`、`release_version`、`code_version`（任意）、`secrets_ref` など。**イメージ更新時**は `release_version` が `manifest/secrets/image/secrets_version_manifest.yml` に存在する必要があります。
- **履歴**: デプロイ成功後に `manifest/secrets/deploy/secrets_deploy_manifest.yml` が追記されます。

---

## 6. Database

### 6.1 マニフェストで SQL を二重管理しない理由

- マイグレーションスクリプトの所在・順序は **`art-gallery-database`** がソース・オブ・トゥルースです。
- 適用済みバージョンは DB の **`schema_migrations`**（またはプロジェクトで採用している同等メカニズム）で管理します。
- release-tools に **SQL 版専用のマニフェスト**を増やすと、DB リポジトリと不整合になりやすいため **作りません**。

### 6.2 ビルド・デプロイで使うもの

- **イメージ**: `build_database.yml` が Postgres 系イメージをビルドし、タグは `release_version`（未指定時はリポジトリ変数 `RELEASE_VERSION`）に合わせます。ビルド成功後は `manifest/database/image/database_version_manifest.yml` 更新の PR を作成します。
- **デプロイ**: `deploy_database.yml` が用途に応じて Ansible プレイブックを順に呼び出します。**コード**は `playbook_deploy_database_code.yml`、**compose + Postgres イメージ**は `playbook_deploy_database_infra.yml`、**マイグレーション**は `playbook_deploy_database_migrate.yml`。一括・タグ指定用に `playbook_deploy_database.yml` も残しています。入力は `run_deploy_code` / `run_deploy_image` / `run_deploy_migrations`、`database_ref`、`database_target_version` など。

### 6.3 ワークフロー上の注意（入力検証）

- **`run_deploy_code` / `run_deploy_image` / `run_deploy_migrations` の少なくとも一方を `true`** にしてください。複数 `true` のときは **コード → インフラ → マイグレーション** の順で実行されます。マイグレーションのみ実行する場合は、Postgres コンテナが既に起動している必要があります。

---

## 7. その他のワークフロー（参照）

| 目的 | ワークフロー |
|:---|:---|
| Nginx ベースイメージビルド（Private リポジトリ） | `build_nginx_base.yml`（art-gallery-nginx-base） |
| Nginx アプリイメージビルド | `build_nginx.yml` |
| Nginx コード版の登録 | `register_nginx_code.yml` |
| WAF シグネチャ更新 | `update_waf_signatures.yml` |
| Nginx デプロイ | `deploy_nginx.yml` |
| Nginx のみリロード | `reload_nginx.yml` |
| 起動サービス設定 | `setup_startup_service.yml` |

---

## 8. 関連ファイル一覧（マニフェスト）

| ファイル | 内容 |
|:---|:---|
| `manifest/version_index.yml` | 各マニフェスト YAML へのパス索引 |
| `manifest/backend/image/backend_version_manifest.yml` | バックエンド **イメージ**タグ ↔ ソース SHA 等 |
| `manifest/backend/code/backend_code_manifest.yml` | バックエンド **コード版**ラベル ↔ ソース SHA 等 |
| `manifest/backend/deploy/backend_deploy_manifest.yml` | 本番デプロイ履歴 |
| `manifest/frontend/image/frontend_version_manifest.yml` | フロント **ビルド**の記録（Artifact 名・ソース SHA 等） |
| `manifest/database/image/database_version_manifest.yml` | Database **イメージ**タグ ↔ ソース SHA 等 |
| `manifest/secrets/image/secrets_version_manifest.yml` | Secrets API **イメージ**タグ ↔ ソース SHA 等 |
| `manifest/secrets/code/secrets_code_manifest.yml` | Secrets API **コード版**ラベル ↔ ソース SHA 等 |
| `manifest/secrets/deploy/secrets_deploy_manifest.yml` | Secrets API 本番デプロイ履歴 |
| `manifest/nginx/image/nginx_version_manifest.yml` | Nginx（アプリ層）**イメージ**タグ ↔ ソース SHA 等 |
| `manifest/nginx/code/nginx_code_manifest.yml` | Nginx **コード版**ラベル ↔ ソース SHA 等 |
| `manifest/nginx/deploy/nginx_deploy_manifest.yml` | Nginx 本番デプロイ履歴 |

SQL 用の追加マニフェストは **置かない**（上記 Database 節の方針）。
