locals {
  azure_ad_v1_issuer_discovery = "https://login.microsoftonline.com/${var.azure_ad_tenant_id}/.well-known/openid-configuration"
  azure_ad_v1_issuer_claim     = "https://sts.windows.net/${var.azure_ad_tenant_id}/"
  keycloak_internal_issuer     = "http://keycloak:8080/realms/${var.keycloak_realm}"
}

resource "konnect_gateway_consumer" "consumer_azure_ad_consumer_1" {
  username         = "azure-ad-consumer-1"
  custom_id        = var.azure_ad_consumer1_client_id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_consumer" "consumer_azure_ad_consumer_2" {
  username         = "azure-ad-consumer-2"
  custom_id        = var.azure_ad_consumer2_client_id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_consumer" "consumer_keycloak_consumer_1" {
  username         = "keycloak-consumer-1"
  custom_id        = "consumer-1"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_consumer" "consumer_keycloak_consumer_2" {
  username         = "keycloak-consumer-2"
  custom_id        = "consumer-2"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_service" "svc_orders_auth_azure" {
  name             = "svc-orders-auth-azure"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_auth_azure" {
  name             = "route-orders-auth-azure"
  methods          = ["GET"]
  paths            = ["/orders/auth/azure"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_auth_azure.id
  }
}

resource "konnect_gateway_plugin_openid_connect" "openid_connect_azure" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_auth_azure.id
  }

  config = {
    issuer                  = local.azure_ad_v1_issuer_discovery
    auth_methods            = ["bearer"]
    bearer_token_param_type = ["header"]
    audience_claim          = ["aud"]
    audience_required       = [var.azure_ad_audience]
    issuers_allowed         = [local.azure_ad_v1_issuer_claim]
    consumer_claims         = [["appid"]]
    consumer_by             = ["custom_id"]
    verify_parameters       = false
  }
}

resource "konnect_gateway_service" "svc_orders_auth_keycloak" {
  name             = "svc-orders-auth-keycloak"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_auth_keycloak" {
  name             = "route-orders-auth-keycloak"
  methods          = ["GET"]
  paths            = ["/orders/auth/keycloak"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_auth_keycloak.id
  }
}

resource "konnect_gateway_plugin_openid_connect" "openid_connect_keycloak" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_auth_keycloak.id
  }

  config = {
    issuer                  = local.keycloak_internal_issuer
    auth_methods            = ["bearer"]
    bearer_token_param_type = ["header"]
    consumer_claims         = [["azp"]]
    consumer_by             = ["custom_id"]
    roles_claim             = ["realm_access", "roles"]
    roles_required          = [var.keycloak_allowed_role]
    verify_parameters       = false
  }
}
