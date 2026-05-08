#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -z "${KONNECT_TOKEN:-}" || -z "${KONNECT_CP_ID:-}" ]]; then
  echo "KONNECT_TOKEN and KONNECT_CP_ID must be set in .env" >&2
  exit 1
fi

wait_for_docker() {
  if docker info >/dev/null 2>&1; then
    return
  fi

  if [[ "$(uname -s)" == "Darwin" ]] && command -v open >/dev/null 2>&1; then
    echo "Starting Docker Desktop"
    open -a Docker >/dev/null 2>&1 || true
  fi

  echo "Waiting for Docker daemon"
  for _ in $(seq 1 90); do
    if docker info >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  echo "Docker daemon did not become ready in time" >&2
  exit 1
}

wait_for_docker

echo "Starting local demo dependencies"
docker compose up -d orders-east orders-west orders-instance-1 orders-instance-2 keycloak

echo "Bootstrapping local Keycloak realm"
python3 scripts/bootstrap_keycloak.py

echo "Initializing Konnect Terraform provider"
terraform -chdir=terraform/konnect init -input=false -upgrade

echo "Applying Konnect control plane configuration"
TF_VAR_konnect_control_plane_id="$KONNECT_CP_ID" \
TF_VAR_azure_ad_tenant_id="${AD_PROTECTED_API_TENANT_ID:-}" \
TF_VAR_azure_ad_audience="${AD_PROTECTED_API_AUDIENCE:-}" \
TF_VAR_azure_ad_consumer1_client_id="${AD_CONSUMER1_CLIENT_ID:-}" \
TF_VAR_azure_ad_consumer2_client_id="${AD_CONSUMER2_CLIENT_ID:-}" \
TF_VAR_keycloak_realm="${KEYCLOAK_REALM:-kong-demo}" \
TF_VAR_keycloak_allowed_role="${KEYCLOAK_ALLOWED_ROLE:-api-access}" \
terraform -chdir=terraform/konnect apply -input=false -auto-approve

echo "Starting Konnect hybrid data plane and demo UI"
docker compose up -d kong-dp demo-ui

echo
echo "Konnect configuration applied"
echo "UI:               http://localhost:8080"
echo "Kong Proxy:        http://localhost:8000"
echo "Kong Proxy TLS:    https://localhost:8443"
echo "Orders East Mock:  http://localhost:9101"
echo "Orders West Mock:  http://localhost:9102"
echo "Instance 1 Mock:   http://localhost:9201"
echo "Instance 2 Mock:   http://localhost:9202"
echo "Keycloak:          http://localhost:8081"
