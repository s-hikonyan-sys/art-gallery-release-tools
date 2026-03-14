#!/bin/bash
# Description: バックエンドサービスが依存するSecrets APIとPostgreSQLが
#              起動し、ヘルスチェックをパスしていることを確認するスクリプト。
#              CI環境での安定性を確保するため、Secrets APIは常にクリーンな状態から起動し、
#              PostgreSQLは既存の状態を維持しつつ必要に応じて起動・ヘルスチェックを行う。

set -euo pipefail # エラー発生時に即座に終了、未定義変数を使用しない、パイプのエラーを捕捉

# グローバル設定 (readonly)
readonly MAX_HEALTH_CHECK_RETRIES=12 # ヘルスチェックの最大試行回数
readonly HEALTH_CHECK_INTERVAL=5     # ヘルスチェックの待機間隔（秒）

# --- ヘルパー関数 ---

# Usage: log_info "message"
# 引数: ${1} - ログメッセージ
# Infoレベルのメッセージを出力する
log_info() {
  echo "$(date -Is) INFO: ${1}"
}

# Usage: log_error "message"
# 引数: ${1} - エラーメッセージ
# Errorレベルのメッセージを出力する
log_error() {
  echo "$(date -Is) ERROR: ${1}" >&2
}

# Usage: get_container_health_status "container_name"
# 引数: ${1} - コンテナ名
# 戻り値: コンテナのヘルスステータス (healthy, unhealthy, starting, missing)
get_container_health_status() {
  local -r container_name="${1}"
  docker inspect --format='{{.State.Health.Status}}' "${container_name}" 2>/dev/null || echo "missing"
}

# Usage: wait_for_condition "description" "check_command" "max_retries" "interval"
# 引数: ${1} - 待機対象の説明（ログ出力用）
#       ${2} - 条件をチェックするコマンド文字列。成功時に終了コード0を返すこと
#       ${3} - 最大試行回数
#       ${4} - 待機間隔（秒）
# 戻り値: 0 (条件が満たされた), 1 (条件が満たされなかった)
wait_for_condition() {
  local -r description="${1}"
  local -r check_command="${2}"
  local -r max_retries="${3}"
  local -r interval="${4}"

  for ((i = 1; i <= max_retries; i++)); do
    if eval "${check_command}"; then
      log_info "${description} is ready."
      return 0 # 正常終了
    fi
    log_info "Waiting for ${description} (attempt ${i}/${max_retries})..."
    sleep "${interval}"
  done

  log_error "${description} did not become ready after ${max_retries} attempts."
  return 1 # 異常終了
}

# Usage: ensure_service_healthy "container_name" "up_command"
# 引数: ${1} - コンテナ名
#       ${2} - サービスを起動するためのDocker Composeコマンド（例: "docker compose up -d secrets-api"）
# サービスがhealthyであることを確認し、必要であれば起動・ヘルスチェックを行う。
# 既にhealthyの場合は早期リターンしてネストを浅くする。
ensure_service_healthy() {
  local -r container_name="${1}"
  local -r up_command="${2}"

  local status
  status=$(get_container_health_status "${container_name}")

  # 既にhealthyであれば、そのまま終了
  if [ "${status}" == "healthy" ]; then
    log_info "${container_name} is already healthy."
    return 0 # 正常終了
  fi

  # healthyでなければ起動を試みる
  log_info "${container_name} is not healthy (current status: ${status}), attempting to start..."
  eval "${up_command}"

  # ヘルスチェックを待機
  if ! wait_for_condition "${container_name} health" \
    "[ \"\$(get_container_health_status '${container_name}')\" = 'healthy' ]" \
    "${MAX_HEALTH_CHECK_RETRIES}" \
    "${HEALTH_CHECK_INTERVAL}"; then
    log_error "Failed to ensure ${container_name} is healthy."
    exit 1
  fi
}


# --- メイン処理 ---

# 引数の取得と検証 (readonly)
readonly DEPLOYMENT_DIR="${1}"
readonly SECRETS_CONTAINER_NAME="${2}"
readonly POSTGRES_CONTAINER_NAME="${3}"

if [ -z "${DEPLOYMENT_DIR}" ] || [ -z "${SECRETS_CONTAINER_NAME}" ] || [ -z "${POSTGRES_CONTAINER_NAME}" ]; then
  log_error "Usage: $0 <deployment_dir> <secrets_container_name> <postgres_container_name>"
  exit 1
fi

log_info "Changing directory to ${DEPLOYMENT_DIR}"
cd "${DEPLOYMENT_DIR}" || { log_error "Failed to change directory to ${DEPLOYMENT_DIR}"; exit 1; }


# Step 1: バックエンドとSecrets APIを停止・削除し、トークンをクリーンアップ
# Secrets APIは使い捨てトークンを発行するため、常にクリーンな状態から起動させる。
# Postgresはデータを保持するため、ここでは停止・削除しない。
# （docker compose stop/rm はサービス名で指定）
log_info "Stopping and removing backend and Secrets API containers (keeping Postgres)..."
docker compose stop backend secrets-api || true
docker compose rm -f backend secrets-api || true

log_info "Deleting secrets tokens from host volume..."
rm -f ./conf/secrets/tokens/database_token.txt || true
rm -f ./conf/secrets/tokens/backend_token.txt || true


# Step 2: Secrets APIがhealthyであることを確認し、必要であれば起動する
# トークンが削除されたため、Secrets APIは必ず起動処理で新しいトークンを生成する。
# （docker compose up はサービス名で指定。compose内のサービス名は secrets-api / postgres）
ensure_service_healthy "${SECRETS_CONTAINER_NAME}" "docker compose up -d secrets-api"

# Secrets APIがhealthyになった後、バックエンド用トークンファイルが生成されるまで待機
readonly BACKEND_TOKEN_FILE_PATH="./conf/secrets/tokens/backend_token.txt"
if ! wait_for_condition "backend token file (${BACKEND_TOKEN_FILE_PATH})" \
  "[ -s \"${BACKEND_TOKEN_FILE_PATH}\" ]" \
  "${MAX_HEALTH_CHECK_RETRIES}" \
  "${HEALTH_CHECK_INTERVAL}"; then
  log_error "Backend token file was not created by Secrets API."
  exit 1
fi


# Step 3: Databaseがhealthyであることを確認し、必要であれば起動する
# Postgresは既存のデータボリュームがあればそれを使用し、なければ初期化される。
ensure_service_healthy "${POSTGRES_CONTAINER_NAME}" "docker compose up -d postgres"


log_info "All backend dependencies (Secrets API, Database) are healthy and ready."
exit 0
