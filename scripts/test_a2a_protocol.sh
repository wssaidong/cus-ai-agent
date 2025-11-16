#!/bin/bash

# ==========================================
# A2A 协议 HTTP 接口 curl 测试脚本
# ==========================================
# 用途:
#   依次调用 /api/v1/a2a 下各端点，验证 A2A AgentCard HTTP 协议是否工作正常。
# 使用:
#   ./scripts/test_a2a_protocol.sh
#   API_BASE_URL=http://127.0.0.1:8000/api/v1/a2a ./scripts/test_a2a_protocol.sh
# ==========================================

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/api/v1/a2a}"
AGENT_NAME="${AGENT_NAME:-my-agent}"
AGENT_VERSION="${AGENT_VERSION:-1.0.0}"

# 颜色
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
NC="\033[0m"

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# 使用 curl 调用接口, 返回值中最后一行是 HTTP 状态码, 前面的内容是响应 body
curl_with_status() {
  local method="$1" url="$2" data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -sS -X "$method" "$url" \
      -H "Content-Type: application/json" \
      -d "$data" \
      -w '\n%{http_code}'
  else
    curl -sS -X "$method" "$url" -w '\n%{http_code}'
  fi
}

# 简单检查: HTTP 200 且 JSON 中 code == 0 (如果系统安装了 jq)
check_response() {
  local step="$1" resp="$2"
  local http_code body
  http_code="$(printf '%s\n' "$resp" | tail -n1)"
  body="$(printf '%s\n' "$resp" | sed '$d')"

  echo "--- ${step} 响应 body ---"
  echo "$body"
  echo "--- ${step} HTTP 状态码: ${http_code} ---"

  if [[ "$http_code" != "200" ]]; then
    log_error "${step} HTTP 状态码不是 200"
    return 1
  fi

  if command -v jq >/dev/null 2>&1; then
    local code msg
    code="$(printf '%s' "$body" | jq -r '.code // empty')" || true
    msg="$(printf '%s' "$body" | jq -r '.message // empty')" || true
    if [[ "$code" == "0" ]]; then
      log_ok "${step} 成功 (code=0, message=${msg})"
    else
      log_error "${step} 失败 (code=${code:-N/A}, message=${msg:-})"
      return 1
    fi
  else
    log_warn "未安装 jq，仅检查到 HTTP 200，未进一步解析 code/message"
    log_ok "${step} HTTP 200"
  fi
}

create_agent_card() {
  log_info "1) 创建 AgentCard (${AGENT_NAME}:${AGENT_VERSION})"
  local payload
  payload='{
    "name": "'"${AGENT_NAME}"'",
    "description": "A2A 协议测试智能体",
    "version": "'"${AGENT_VERSION}"'",
    "url": "http://127.0.0.1:8000/a2a/v1",
    "protocol_version": "0.2.9",
    "preferred_transport": "JSONRPC",
    "registration_type": "SERVICE",
    "skills": [
      {
        "id": "chat",
        "name": "对话",
        "description": "智能对话功能",
        "tags": ["chat", "conversation"],
        "inputModes": ["application/json"],
        "outputModes": ["application/json"]
      }
    ]
  }'

  local resp
  resp="$(curl_with_status POST "${API_BASE_URL}/agent-cards" "$payload")"
  check_response "创建 AgentCard" "$resp"
}

get_agent_card() {
  log_info "2) 获取 AgentCard 详情"
  local url
  url="${API_BASE_URL}/agent-cards/${AGENT_NAME}?version=${AGENT_VERSION}&registration_type=SERVICE"
  local resp
  resp="$(curl_with_status GET "$url")"
  check_response "获取 AgentCard" "$resp"
}

list_agent_cards() {
  log_info "3) 列出 AgentCard 列表"
  local url
  url="${API_BASE_URL}/agent-cards?page_no=1&page_size=10"
  local resp
  resp="$(curl_with_status GET "$url")"
  check_response "列出 AgentCard" "$resp"
}

get_agent_versions() {
  log_info "4) 获取 AgentCard 版本列表"
  local url
  url="${API_BASE_URL}/agent-cards/${AGENT_NAME}/versions"
  local resp
  resp="$(curl_with_status GET "$url")"
  check_response "获取版本列表" "$resp"
}

delete_agent_card() {
  log_info "5) 删除 AgentCard"
  local url
  url="${API_BASE_URL}/agent-cards/${AGENT_NAME}?version=${AGENT_VERSION}"
  local resp
  resp="$(curl_with_status DELETE "$url")"
  check_response "删除 AgentCard" "$resp"
}

main() {
  log_info "使用 API_BASE_URL=${API_BASE_URL} 测试 A2A HTTP 协议"

  create_agent_card
  get_agent_card
  list_agent_cards
  get_agent_versions
  delete_agent_card

  log_ok "A2A HTTP 协议全链路 curl 测试完成"
}

main "$@"

