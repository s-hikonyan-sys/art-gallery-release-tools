# art-gallery-release-tools

![IaC](https://img.shields.io/badge/IaC-Ansible-blue) ![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF) ![Docker](https://img.shields.io/badge/Container-Docker-2496ED)

このリポジトリは、プロジェクト全体のインフラ構築、デプロイ、およびリリース管理を担う中央ハブです。

## 概要

マルチレポ構成における各コンポーネント（Backend, Frontend, Nginx, Database, Secrets API）を統合し、Ansible および GitHub Actions を用いて一貫性のあるデプロイ環境を提供します。

## 重要なドキュメント

- **[機密情報・暗号化運用ガイド](ansible/vault/README.md)**: GitHub Secrets を活用した事前暗号化フロー、および機密情報配布専用コンテナ（Secrets API）のライフサイクルについての詳細。

## 特徴

- **事前暗号化シークレット (Pre-encrypted Secrets)**: 機密情報は事前に Fernet で暗号化され、GitHub Actions Secrets から直接デプロイされます。CI は暗号化済みの値をそのままファイルに書き出すだけのシンプルなフローを採用しています。
- **Ephemeral Secrets（使い捨て機密情報配布）**: データベースパスワード等の配布を専用コンテナ（`art-gallery-secrets-api`）に分離しています。コンテナ起動時のワンタイムトークンを用いた認証を経て各サービスにパスワードを配布後、コンテナ自身が自動停止することでセキュリティリスクを最小化しています。
- **イメージとコードの分離**: Docker イメージには実行環境（OS・ミドルウェア）のみを内包し、アプリケーションコードはデプロイ時にボリュームマウントで提供する設計を採用しています。
- **完全手動デプロイ**: 意図しない更新を防ぐため、すべてのデプロイ・ビルド処理は GitHub Actions の `workflow_dispatch` から手動で実行します。「イメージのみの更新」と「コードのみの反映」を独立してトリガー可能です。
- **集中依存関係管理**: 各アプリケーションの `Dockerfile` や `requirements.txt` などを本リポジトリで一元管理し、実行環境の整合性を保証します。

## 機密情報のデプロイフロー

1. **事前準備**: 管理者がローカルで `art-gallery-secrets` の `SecretManager` を用いてパスワードを Fernet 暗号化し、GitHub Secrets に `PROD_SECRET_KEY` と `PROD_DB_PASSWORD_ENCRYPTED` として登録します。
2. **デプロイ**: GitHub Actions の `write-secrets-files` アクションが、Secrets の値をそのまま `secrets.yaml.encrypted` および `config.yaml` として出力し、Ansible がサーバーへ配置します。
3. **実行時**: `secrets-api` コンテナが起動し、配布された暗号化ファイルを復号。各サービスへワンタイムトークン経由でパスワードを提供します。

## ディレクトリ構成

- `.github/`: CI/CD ワークフローおよびシークレット書き出し用のカスタムアクション（`write-secrets-files`）
- `ansible/`: デプロイおよび構築用の Ansible Playbook 一式
  - `group_vars/`: 全環境共通の基幹変数定義
  - `inventory/`: 環境定義 (ci.yml, production.yml)
  - `roles/`: 各サービスごとの構築・設定ロール（backend, database, docker, secrets 等）
  - `vault/`: 暗号化関連のテンプレートとドキュメント
