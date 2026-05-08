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

if [[ -n "${KONNECT_TOKEN:-}" && -n "${KONNECT_CP_ID:-}" ]]; then
  echo "Destroying Konnect-managed demo entities"
  TF_VAR_konnect_control_plane_id="$KONNECT_CP_ID" \
  terraform -chdir=terraform/konnect destroy -input=false -auto-approve || true
fi

if docker info >/dev/null 2>&1; then
  echo "Stopping local demo containers"
  docker compose down --remove-orphans --timeout 20
fi

echo "Cleaning Terraform runtime state"
rm -rf terraform/konnect/.terraform
rm -f terraform/konnect/.terraform.lock.hcl
rm -f terraform/konnect/terraform.tfstate
rm -f terraform/konnect/terraform.tfstate.backup
rm -f terraform/konnect/.terraform.tfstate.lock.info

echo "Cleanup complete"
