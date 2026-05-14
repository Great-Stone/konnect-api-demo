resource "konnect_gateway_service" "svc_datakit_fallback" {
  name             = "svc-datakit-fallback"
  protocol         = "http"
  host             = "datakit-api1"
  port             = 9401
  path             = "/datakit/api1/fallback"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_datakit_fallback" {
  name             = "route-datakit-fallback"
  methods          = ["GET"]
  paths            = ["/orders/datakit/fallback"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_datakit_fallback.id
  }
}

resource "konnect_gateway_plugin_openid_connect" "openid_connect_datakit_fallback" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_datakit_fallback.id
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

resource "konnect_gateway_service" "svc_datakit_combine" {
  name             = "svc-datakit-combine"
  protocol         = "http"
  host             = "datakit-api1"
  port             = 9401
  path             = "/datakit/api1/accounts"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_datakit_combine" {
  name             = "route-datakit-combine"
  methods          = ["GET"]
  paths            = ["/orders/datakit/combine"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_datakit_combine.id
  }
}

resource "konnect_gateway_plugin_openid_connect" "openid_connect_datakit_combine" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_datakit_combine.id
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

resource "konnect_gateway_service" "svc_datakit_cache" {
  name             = "svc-datakit-cache"
  protocol         = "http"
  host             = "datakit-api1"
  port             = 9401
  path             = "/datakit/api1/cache-source"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_datakit_cache" {
  name             = "route-datakit-cache"
  methods          = ["GET"]
  paths            = ["/orders/datakit/cache"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_datakit_cache.id
  }
}

resource "konnect_gateway_plugin_openid_connect" "openid_connect_datakit_cache" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_datakit_cache.id
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

resource "terraform_data" "configure_datakit_plugins" {
  triggers_replace = [
    var.konnect_control_plane_id,
    var.konnect_token,
    var.konnect_server_url,
    konnect_gateway_route.route_datakit_fallback.id,
    konnect_gateway_route.route_datakit_combine.id,
    konnect_gateway_route.route_datakit_cache.id,
    filesha256("${path.root}/../../scripts/configure_datakit.py"),
  ]

  provisioner "local-exec" {
    command = "python3 ${path.root}/../../scripts/configure_datakit.py"
    environment = {
      KONNECT_CP_ID      = var.konnect_control_plane_id
      KONNECT_TOKEN      = var.konnect_token
      KONNECT_SERVER_URL = var.konnect_server_url
    }
  }

  depends_on = [
    konnect_gateway_plugin_openid_connect.openid_connect_datakit_fallback,
    konnect_gateway_plugin_openid_connect.openid_connect_datakit_combine,
    konnect_gateway_plugin_openid_connect.openid_connect_datakit_cache,
  ]
}
