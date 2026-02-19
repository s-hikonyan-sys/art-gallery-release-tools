# art-gallery-release-tools

![IaC](https://img.shields.io/badge/IaC-Ansible-blue) ![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF) ![Docker](https://img.shields.io/badge/Container-Docker-2496ED)

このリポジトリは、プロジェクト全体のインフラ構築、デプロイ、およびリリース管理を担う中央ハブです。

## 概要

マルチレポ構成における各コンポーネント（Backend, Frontend, Nginx, Database, Secrets API）を統合し、Ansible および GitHub Actions を用いて一貫性のあるデプロイ環境を提供します。

## 重要なドキュメント

- **[機密情報・暗号化運用ガイド](ansible/vault/README.md)**: 
  Ansible Vault と Fernet 暗号化を組み合わせた多段パスワード管理フロー、および機密情報配布専用コンテナ（Secrets API）のライフサイクルについての詳細。デプロイ前に必ず一読してください。

## 特徴

- **多段・使い捨ての機密情報管理 (Ephemeral Secrets)**: 
  データベースパスワード等の配布を専用コンテナに分離しています。コンテナ起動時のワンタイムトークンを用いた認証を経て各サービスにパスワードを配布後、コンテナ自身が自動停止することでセキュリティリスクを最小化しています。
- **イメージとコードの分離**: 
  Docker イメージには実行環境（OS・ミドルウェア）のみを内包し、アプリケーションコードはデプロイ時にボリュームマウントで提供する設計を採用しています。
- **完全手動デプロイ**: 
  意図しない更新を防ぐため、すべてのデプロイ・ビルド処理は GitHub Actions の `workflow_dispatch` から手動で実行します。「イメージのみの更新」と「コードのみの反映」を独立してトリガー可能です。
- **集中依存関係管理**: 
  各アプリケーションの `Dockerfile` や `requirements.txt` などを本リポジトリで一元管理し、実行環境の整合性を保証します。

## ディレクトリ構成

- `.github/`: CI/CD ワークフローおよび Ansible Vault 動的生成用の共通カスタムアクション
- `ansible/`: デプロイおよび構築用の Ansible Playbook 一式
  - `group_vars/`: 全環境共通の基幹変数定義
  - `inventory/`: 環境定義 (ci.yml, production.yml)
  - `roles/`: 各サービスごとの構築・設定ロール（backend, database, docker, frontend, nginx, secrets）
  - `scripts/`: 暗号化ブリッジ用 Python スクリプト
  - `vault/`: 暗号化関連のテンプレートとドキュメント