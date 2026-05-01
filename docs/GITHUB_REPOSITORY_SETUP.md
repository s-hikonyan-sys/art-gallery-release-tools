# GitHub リポジトリ設定（release-tools 運用の前提）

`art-gallery-release-tools` の GitHub Actions は、ビルド・デプロイ成功後に **マニフェストやデプロイ履歴を追記したブランチを push し、`gh pr create` 相当でプルリクエストを開く** 処理を含みます（`create-build-manifest-pr` / `create-deploy-manifest-pr` など）。

リポジトリ側で次の設定が無効だと、デプロイやビルド自体は成功しても **PR 作成だけが失敗**します。

---

## 1. Workflow permissions（書き込み）

1. リポジトリの **Settings** → **Actions** → **General** を開く。
2. **Workflow permissions** で **Read and write permissions** を選ぶ。  
   （read-only のままだと、Actions からの `git push` が 403 になることがあります。）
3. **Save** を押す。

---

## 2. Actions による PR 作成の許可

1. 同じ **Settings** → **Actions** → **General** 画面の **Workflow permissions** 付近にある  
   **Allow GitHub Actions to create and approve pull requests** にチェックを入れる。
2. **Save** を押す。

> このチェックがオフのままだと、ブランチ push までは成功しても PR 作成で次のようなエラーになります。  
> `GitHub Actions is not permitted to create or approve pull requests (createPullRequest)`

---

## 3. ワークフロー側の `permissions` について

各ワークフローで `contents: write` および必要に応じて `pull-requests: write` を宣言している場合がありますが、**上記リポジトリ設定（特に「Allow GitHub Actions to create and approve pull requests」）がオフだと、宣言だけでは PR は作成できません。** リポジトリ設定とセットで有効にしてください。

---

## 4. 他ドキュメントとの位置づけ

| ドキュメント | 内容 |
|:---|:---|
| 本書 | **GitHub 上の release-tools リポジトリ**の設定（Actions・PR 前提）。 |
| [SERVER_SETUP.md](SERVER_SETUP.md) | **本番 VPS** の OS・パッケージ・ディレクトリ等の初期構築。 |
| [BUILD_AND_DEPLOY.md](../BUILD_AND_DEPLOY.md) | ビルド／デプロイ手順とマニフェストの役割。 |
| [README.md](../README.md) | リポジトリ全体の概要とディレクトリ構成。 |

初めて release-tools を運用する場合は、**本書 → Secrets / Variables 登録 → サーバー準備（SERVER_SETUP）** の順で確認すると手戻りが少なくなります。
