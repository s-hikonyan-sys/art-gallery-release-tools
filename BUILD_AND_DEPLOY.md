# ビルド・デプロイとバージョン管理

このドキュメントは、`art-gallery-release-tools` における **ビルド／デプロイの手順**と、**どのファイルがバージョン・成果物とどう紐づくか**をまとめたものです。詳細な全体像は [README.md](README.md) を参照してください。

## 1. 方針の要約

- **手動デプロイ**: 各ワークフローは原則 `workflow_dispatch` で実行します。
- **マニフェストの役割**: Git タグに依存せず、release-tools 上の YAML で **イメージタグ ↔ ソースコミット ↔ ビルド記録** を追跡できるようにします。
- **インデックス**: サービス別マニフェストのパスは `version_manifest.yml` で参照用にまとめています（人間向けの索引）。

```yaml
# version_manifest.yml（抜粋）
frontend_manifest_path: "frontend_version_manifest.yml"
backend_manifest_path: "backend_version_manifest.yml"
```

- **Database（SQL）**: **SQL の版管理を release-tools のマニフェストで二重に持たない**方針です。スキーマの正は **`art-gallery-database` のディレクトリ（例: `migrations/v…/`）と、実行後の DB 側 `schema_migrations`** です。release-tools に SQL 専用のマニフェストは置きません。

---

## 2. コンポーネント別の実装状況（○ / △ / ✗）

凡例: **○** 実装済み / **△** 一部（マニフェストや運用が Backend ほど集約されていない） / **✗** 未実装

| コンポーネント | ビルド用 WF | デプロイ用 WF | マニフェスト・トレーサビリティ |
|:---|:---:|:---:|:---|
| **Backend** | `build_backend.yml` | `deploy_backend.yml` | **○** `backend_version_manifest.yml`（イメージ） / `backend_code_manifest.yml`（コード版・`register_backend_code.yml` が更新） / `backend_deploy_manifest.yml`（本番デプロイ履歴） |
| **Frontend** | `build_frontend.yml` | `deploy_frontend.yml` | **○** `frontend_version_manifest.yml`（ビルド記録・PR 更新）。デプロイは **GitHub Actions の Artifact**（`frontend-dist-<version>`）を名前で解決 |
| **Database** | `build_database.yml` | `deploy_database.yml` | **△** イメージは `release_version`（リポジトリ変数または入力）でタグ付け。**SQL の版は DB リポジトリ＋`schema_migrations` が正**（下記「Database」） |
| **Nginx** | `build_nginx.yml` | `deploy_nginx.yml` / `reload_nginx.yml` | **△** 専用のバージョンマニフェスト YAML はなく、`release_version` と `nginx_ref` 等で運用 |
| **Secrets API** | `build_secrets.yml` | `deploy_secrets.yml` | **△** 同上（専用マニフェストファイルなし、`release_version` + `secrets_ref`） |

---

## 3. Backend

- **イメージビルド**: `build_backend.yml` → GHCR プッシュ後、`backend_version_manifest.yml` 更新の PR。
- **コード版の登録**: `register_backend_code.yml` → `backend_code_manifest.yml` 更新の PR。
- **デプロイ**: `deploy_backend.yml` の入力 `run_deploy_image` / `run_deploy_code`、`release_version`、`code_version`（任意）、`backend_ref` など。**イメージ更新時**は `release_version` が `backend_version_manifest.yml` に存在する必要があります。
- **履歴**: デプロイ成功後に `backend_deploy_manifest.yml` が追記されます。

詳細な表と推奨フローは [README.md の「Backend のバージョン管理」](README.md#backend-のバージョン管理マニフェスト) を参照してください。

---

## 4. Frontend（リポジトリと release-tools の役割分担）

| 場所 | 役割 |
|:---|:---|
| **art-gallery-frontend** | CI は **lint・テストまで**（本番ビルドや Artifact 登録・マニフェスト更新は行わない想定）。 |
| **art-gallery-release-tools** | **`build_frontend.yml`**: 別リポジトリをチェックアウト（トークン使用）→ lint / test / `npm run build` → **Artifact アップロード** → `frontend_version_manifest.yml` 更新 PR。**`deploy_frontend.yml`**: 同じバージョン名の Artifact を取得してサーバーへ展開。 |

- フロントの **本番向けビルド・Artifact・マニフェスト** は release-tools に集約し、**機密トークンやマニフェストの更新権限**も release-tools 側のシークレット・ワークフローで管理する方針です。
- デプロイ前に、対象 `release_version` で **`build_frontend.yml` が成功済み**であること（Artifact が残っていること）が必要です。

---

## 5. Database

### 5.1 マニフェストで SQL を二重管理しない理由

- マイグレーションスクリプトの所在・順序は **`art-gallery-database`** がソース・オブ・トゥルースです。
- 適用済みバージョンは DB の **`schema_migrations`**（またはプロジェクトで採用している同等メカニズム）で管理します。
- release-tools に **SQL 版専用のマニフェスト**を増やすと、DB リポジトリと不整合になりやすいため **作りません**。

### 5.2 ビルド・デプロイで使うもの

- **イメージ**: `build_database.yml` が Postgres 系イメージをビルドし、タグは `release_version`（未指定時はリポジトリ変数 `RELEASE_VERSION`）に合わせます。
- **デプロイ**: `deploy_database.yml` の `run_deploy_image` / `run_deploy_code` / `run_deploy_migrations`、`database_ref`、`database_target_version` など。Ansible 経由でサーバー上のリポジトリ取得・マイグレーション実行に使われます。

### 5.3 ワークフロー上の注意（入力検証）

- 現状の `deploy_database.yml` では、**`run_deploy_image` または `run_deploy_migrations` の少なくとも一方を `true`** にしないと検証エラーになります。コード（マイグレーション以外）のみ更新する場合の扱いは、運用に合わせて入力の組み合わせを確認してください。

---

## 6. その他のワークフロー（参照）

| 目的 | ワークフロー |
|:---|:---|
| Nginx イメージビルド | `build_nginx.yml` |
| Secrets API イメージビルド | `build_secrets.yml` |
| Nginx デプロイ | `deploy_nginx.yml` |
| Secrets API デプロイ | `deploy_secrets.yml` |
| Nginx のみリロード | `reload_nginx.yml` |
| 起動サービス設定 | `setup_startup_service.yml` |

---

## 7. 関連ファイル一覧（マニフェスト）

| ファイル | 内容 |
|:---|:---|
| `version_manifest.yml` | フロント／バックエンド用マニフェストファイル名の索引 |
| `backend_version_manifest.yml` | バックエンド **イメージ**タグ ↔ ソース SHA 等 |
| `backend_code_manifest.yml` | バックエンド **コード版**ラベル ↔ ソース SHA 等 |
| `backend_deploy_manifest.yml` | 本番デプロイ履歴 |
| `frontend_version_manifest.yml` | フロント **ビルド**の記録（Artifact 名・ソース SHA 等） |

SQL 用の追加マニフェストは **置かない**（上記 Database 節の方針）。
