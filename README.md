# art-gallery-release-tools

このリポジトリは、プロジェクト全体のインフラ構築、デプロイ、およびリリース管理を担う中央ハブです。

## 概要

マルチレポ構成における各コンポーネント（Backend, Frontend, Nginx, Database）を統合し、Ansible および GitHub Actions を用いて一貫性のあるデプロイ環境を提供します。

## 重要なドキュメント

- **[機密情報・暗号化運用ガイド](ansible/vault/README.md)**: 
  Ansible Vault と Fernet 暗号化を組み合わせた多段パスワード管理フローについての詳細。デプロイ前に必ず一読してください。

## 特徴

- **イメージとコードの分離**: Docker イメージには実行環境のみを内包し、コードはボリュームマウントで提供する設計を採用しています。
- **完全手動デプロイ**: 意図しない更新を防ぐため、すべてのデプロイ・ビルド処理は GitHub Actions の `workflow_dispatch` から手動で実行します。
- **集中依存関係管理**: Backend の `requirements.txt` などを本リポジトリで一元管理し、実行環境の整合性を保証します。

## ディレクトリ構成

- `.github/`: CI/CD ワークフローおよび共通カスタムアクション
- `ansible/`: デプロイおよび構築用の Ansible Playbook 一式
  - `roles/`: 各サービスごとの構築・設定ロール
  - `vault/`: 暗号化関連のテンプレートとドキュメント
  - `scripts/`: 暗号化ブリッジ用 Python スクリプト
- `vault/`: (一時的な作業ディレクトリ、Git 管理対象外)
