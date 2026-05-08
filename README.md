# Konnect API Demo

This project is a local demo environment for **Konnect hybrid** scenarios built around a local Kong data plane, Terraform-provisioned Kong entities, mock upstreams, and a scene-based UI.

## Table Of Contents

- [Prerequisites](#prerequisites)
  - [Konnect](#konnect)
  - [Local Tooling](#local-tooling)
  - [Local Files](#local-files)
- [Current Scope](#current-scope)
- [Provisioning Model](#provisioning-model)
- [Local Runtime Shape](#local-runtime-shape)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Certificates](#certificates)
- [Run](#run)
- [Demo Scenes](#demo-scenes)
  - [Traffic And Routing](#traffic-and-routing)
  - [Traffic Control](#traffic-control)
  - [Resilience](#resilience)
  - [Identity](#identity)
- [Terraform Layout](#terraform-layout)
- [Repository Notes](#repository-notes)
- [References](#references)

## Prerequisites

### Konnect

- An existing Konnect control plane
- A valid Konnect personal access token
- Konnect hybrid control plane bootstrap details for the local data plane

### Local Tooling

- Docker Desktop
- Terraform
- Python 3
- Git
- GitHub CLI (`gh`) if you want to create and push the repo from the command line

### Local Files

- A local `.env` file populated from `.env-example`
- Konnect hybrid client certificate and private key under `certs/`

## Current Scope

- Header-based routing
- Service-level and consumer-level rate limiting
- Weighted load balancing
- Failover and circuit-breaker style health-check behavior
- Azure AD token validation with Kong `openid-connect`
- Keycloak role-based authorization with Kong `openid-connect`

## Provisioning Model

All Kong / Konnect entities are managed with Terraform.

That includes:

- services
- routes
- plugins
- consumers
- credentials
- upstreams
- targets

Keycloak itself is bootstrapped locally by a script. It is not managed by Terraform in this repo.

## Local Runtime Shape

The local runtime uses:

- `kong-dp`
- `demo-ui`
- `orders-east`
- `orders-west`
- `orders-instance-1`
- `orders-instance-2`
- `keycloak`

There is no local Kong control plane or local Postgres in this repo.

## Configuration

### Environment Variables

Copy `.env-example` to `.env` and populate the required values.

Important values include:

- `KONNECT_TOKEN`
- `KONNECT_CONTROL_PLANE_NAME`
- `KONNECT_CP_ID`
- `KONNECT_CLUSTER_CONTROL_PLANE`
- `KONNECT_CLUSTER_SERVER_NAME`
- `KONNECT_CLUSTER_TELEMETRY_ENDPOINT`
- `KONNECT_CLUSTER_TELEMETRY_SERVER_NAME`
- Azure AD tenant, audience, and client credentials
- Keycloak bootstrap and demo client values

### Certificates

Place the Konnect hybrid client materials in:

- `certs/public.cer`
- `certs/private.key`

The private key is intentionally excluded from source control.

## Run

Start the full demo stack and apply Konnect configuration:

```bash
./start-demo.sh
```

Stop the local stack and clean up local state:

```bash
./stop-demo.sh
```

When the stack is up, the main endpoints are:

- UI: `http://localhost:8080`
- Kong Proxy: `http://localhost:8000`
- Keycloak: `http://localhost:8081`

## Demo Scenes

### Traffic And Routing

- Header-based routing using `x-region`
- Catch-all policy for missing routing input

### Traffic Control

- Anonymous service-level fixed-window rate limiting
- Consumer-based fixed-window rate limiting

### Resilience

- 30:70 weighted load balancing
- Active and passive health checks
- Failover and recovery with container stop/start controls

### Identity

- Azure AD token validation
- Keycloak role-based authorization
- Kong consumer identification from token claims

Current claim mapping:

- Azure AD: `appid -> Kong Consumer custom_id`
- Keycloak: `azp -> Kong Consumer custom_id`

## Terraform Layout

Konnect Terraform is under:

- `terraform/konnect/versions.tf`
- `terraform/konnect/provider.tf`
- `terraform/konnect/header_routing.tf`
- `terraform/konnect/rate_limiting.tf`
- `terraform/konnect/resilience.tf`
- `terraform/konnect/identity.tf`

## Repository Notes

- Local markdown working notes are intentionally not part of the repository.
- `.env` is intentionally not part of the repository.
- Terraform state is intentionally not part of the repository.
- The private certificate key is intentionally not part of the repository.

## References

- Konnect overview: https://developer.konghq.com/konnect/
- Hybrid mode: https://developer.konghq.com/gateway/hybrid-mode/
- Konnect Terraform provider: https://registry.terraform.io/providers/Kong/konnect/latest
- Provider source: https://github.com/Kong/terraform-provider-konnect
