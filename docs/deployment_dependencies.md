# デプロイ時のコンテナ依存関係（Secrets API / PostgreSQL / Backend）

このリポジトリの Ansible は、**使い捨てトークン方式の Secrets API** と **PostgreSQL**、**Backend** の起動順・健全性を前提にしています。  
`docker-compose.yml` の `depends_on` は初回の `docker compose up` に効きやすく、**手動で個別サービスだけ起動したり、Ansible が `docker compose restart` だけ叩く場合**は依存コンテナが止まったままになり得ます。そのギャップを埋めるのが、ロール `docker` の共通タスクです。

## 依存の概要

1. **Secrets API**  
   トークン発行・シークレット取得 API。トークン消費後はコンテナが **Exited(0)** になり得る。
2. **PostgreSQL**  
   起動時（`postgres-entrypoint.sh`）およびマイグレーション時に、Secrets API へ HTTP でパスワードを取得する。
3. **Backend**  
   Secrets API と PostgreSQL の両方が利用可能であることが前提（設定・トークンファイルなど）。

**Backend が Database コンテナを「操作して起動する」ことは設計上 NG** です。代わりに、**ホスト側（Ansible または運用者）が** Secrets / Postgres を必要な状態にしてから Backend を起動します。

## Ansible での保証（冪等な「最低限の準備」）

| タスクファイル | 内容 |
|----------------|------|
| `roles/docker/tasks/ensure_secrets_healthy.yml` | `secrets-api` が `healthy` でなければ `docker compose up -d secrets-api` し、待機する。 |
| `roles/docker/tasks/ensure_postgres_healthy.yml` | PostgreSQL が `healthy` でなければ `docker compose up -d postgres` し、待機する。 |

これらは次の場面で **include** されます。

- DB マイグレーション（`roles/database/tasks/migrate.yml`）の先頭 … **Secrets のみ**（マイグレは postgres コンテナ内から curl するため postgres 自体は別タスクで前提）
- Postgres の start / restart
- Backend の start / restart（Secrets のあと **Postgres も** 保証）
- Postgres イメージ更新（`update_postgres_image.yml`）の pull 前

**コンテナ内の entrypoint やシェルは、Docker ホスト上で別コンテナを起動できません。**  
そのため「隣のコンテナが落ちていたら起こす」オーケストレーションは **Ansible（または compose 全体の up）側の責務**です。

## `ensure_backend_dependencies.sh` との役割分担

`roles/docker/files/ensure_backend_dependencies.sh` は主に **`update_backend_image`** から呼ばれ、次を**まとめて**行います。

- Backend / Secrets API の停止・削除
- ホスト上のトークンファイル削除（クリーンな再発行）
- Secrets API・PostgreSQL の起動とヘルス待ち
- Backend 用トークンファイル生成待ち

**Ansible の `ensure_*_healthy` だけでは「トークンを捨てて作り直す」までは行いません。**  
イメージ更新時に確実に新トークンへ寄せたい要件と、SSH で入ったときに一発で同じ手順を再現したい要件の両方に、このシェルが効きます。

処理が二重に見えるのは意図的です。

- **Playbook 経由の start / restart / migrate** … 軽い共通タスクで依存の穴を塞ぐ（冪等）。
- **Backend イメージ更新＋手動復旧** … クリーンアップ込みの一括スクリプト。

将来的にシェルを Ansible タスクへ分解したり、一部を Python に寄せる検討は Issue などで別管理してよいです。

## 関連ファイル

- `ansible/roles/docker/tasks/ensure_secrets_healthy.yml`
- `ansible/roles/docker/tasks/ensure_postgres_healthy.yml`
- `ansible/roles/docker/files/ensure_backend_dependencies.sh`
- `ansible/roles/docker/templates/docker-compose.yml.j2`（`depends_on` / `healthcheck`）
