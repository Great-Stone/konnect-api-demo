resource "konnect_gateway_service" "svc_orders_version_v1" {
  name             = "svc-orders-version-v1"
  protocol         = "http"
  host             = "orders-v1"
  port             = 9301
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_service" "svc_orders_version_v2" {
  name             = "svc-orders-version-v2"
  protocol         = "http"
  host             = "orders-v2"
  port             = 9302
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_version_path_v1" {
  name             = "route-orders-version-path-v1"
  methods          = ["GET"]
  paths            = ["/api/v1/orders"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_version_v1.id
  }
}

resource "konnect_gateway_route" "route_orders_version_path_v2" {
  name             = "route-orders-version-path-v2"
  methods          = ["GET"]
  paths            = ["/api/v2/orders"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_version_v2.id
  }
}

resource "konnect_gateway_route" "route_orders_version_header_v1" {
  name             = "route-orders-version-header-v1"
  methods          = ["GET"]
  paths            = ["/orders/version/header"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id
  headers = {
    x-api-version = ["v1"]
  }

  service = {
    id = konnect_gateway_service.svc_orders_version_v1.id
  }
}

resource "konnect_gateway_route" "route_orders_version_header_v2" {
  name             = "route-orders-version-header-v2"
  methods          = ["GET"]
  paths            = ["/orders/version/header"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id
  headers = {
    x-api-version = ["v2"]
  }

  service = {
    id = konnect_gateway_service.svc_orders_version_v2.id
  }
}

resource "konnect_gateway_service" "svc_orders_canary_primary" {
  name             = "svc-orders-canary-primary"
  protocol         = "http"
  host             = "orders-v1"
  port             = 9301
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_canary_40" {
  name             = "route-orders-canary-40"
  methods          = ["GET"]
  paths            = ["/orders/canary/40"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_canary_primary.id
  }
}

resource "konnect_gateway_plugin_canary" "orders_canary_40" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_40.id
  }

  config = {
    upstream_host = "orders-v2"
    upstream_port = 9302
    percentage    = 40
    hash          = "none"
    steps         = 100
  }
}

resource "konnect_gateway_route" "route_orders_canary_time" {
  name             = "route-orders-canary-time"
  methods          = ["GET"]
  paths            = ["/orders/canary/time"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_canary_primary.id
  }
}

resource "konnect_gateway_plugin_canary" "orders_canary_time" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_time.id
  }

  config = {
    upstream_host = "orders-v2"
    upstream_port = 9302
    hash          = "none"
    steps         = 20
    duration      = 120
  }
}

resource "konnect_gateway_route" "route_orders_canary_header" {
  name             = "route-orders-canary-header"
  methods          = ["GET"]
  paths            = ["/orders/canary/header"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_canary_primary.id
  }
}

resource "konnect_gateway_plugin_canary" "orders_canary_header" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_header.id
  }

  config = {
    upstream_host         = "orders-v2"
    upstream_port         = 9302
    hash                  = "none"
    steps                 = 100
    percentage            = 0
    canary_by_header_name = "x-canary-version"
  }
}

resource "konnect_gateway_route" "route_orders_canary_consumer" {
  name             = "route-orders-canary-consumer"
  methods          = ["GET"]
  paths            = ["/orders/canary/consumer"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_canary_primary.id
  }
}

resource "konnect_gateway_consumer" "consumer_pilot" {
  username         = "consumer-pilot"
  custom_id        = "consumer-pilot"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_consumer" "consumer_standard_lifecycle" {
  username         = "consumer-standard-lifecycle"
  custom_id        = "consumer-standard-lifecycle"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_pilot_key" {
  key              = "key-consumer-pilot"
  consumer_id      = konnect_gateway_consumer.consumer_pilot.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_standard_lifecycle_key" {
  key              = "key-consumer-standard-lifecycle"
  consumer_id      = konnect_gateway_consumer.consumer_standard_lifecycle.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_acl" "consumer_pilot_acl" {
  group            = "canary-allow"
  consumer_id      = konnect_gateway_consumer.consumer_pilot.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_acl" "consumer_standard_lifecycle_acl" {
  group            = "standard-access"
  consumer_id      = konnect_gateway_consumer.consumer_standard_lifecycle.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_plugin_key_auth" "orders_canary_consumer_auth" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_consumer.id
  }

  config = {
    key_names        = ["apikey"]
    hide_credentials = false
  }
}

resource "konnect_gateway_plugin_acl" "orders_canary_consumer_acl" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_consumer.id
  }

  config = {
    allow                   = ["canary-allow", "standard-access"]
    hide_groups_header      = true
    include_consumer_groups = true
  }
}

resource "konnect_gateway_plugin_canary" "orders_canary_consumer" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_canary_consumer.id
  }

  config = {
    upstream_host         = "orders-v2"
    upstream_port         = 9302
    canary_by_header_name = "x-canary-version"
    hash                  = "none"
    steps                 = 100
    percentage            = 0
  }
}

resource "konnect_gateway_service" "svc_orders_deprecation_v1" {
  name             = "svc-orders-deprecation-v1"
  protocol         = "http"
  host             = "orders-v1"
  port             = 9301
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_service" "svc_orders_deprecation_v2" {
  name             = "svc-orders-deprecation-v2"
  protocol         = "http"
  host             = "orders-v2"
  port             = 9302
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_deprecation_v1" {
  name             = "route-orders-deprecation-v1"
  methods          = ["GET"]
  paths            = ["/orders/deprecation/v1"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_deprecation_v1.id
  }
}

resource "konnect_gateway_plugin_response_transformer" "orders_deprecation_v1_headers" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_deprecation_v1.id
  }

  config = {
    add = {
      headers = [
        "Deprecation:true",
        "Sunset:Tue, 30 Jun 2026 23:59:59 GMT",
        "Link:</api/v2/orders>; rel=\"successor-version\"",
        "Warning:299 - \"API v1 is deprecated; migrate to v2\"",
      ]
    }
  }
}

resource "konnect_gateway_route" "route_orders_deprecation_v2" {
  name             = "route-orders-deprecation-v2"
  methods          = ["GET"]
  paths            = ["/orders/deprecation/v2"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_deprecation_v2.id
  }
}

resource "konnect_gateway_route" "route_orders_deprecation_sunset" {
  name             = "route-orders-deprecation-sunset"
  methods          = ["GET"]
  paths            = ["/orders/deprecation/v1/sunset"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_deprecation_v1.id
  }
}

resource "konnect_gateway_plugin_request_termination" "orders_deprecation_sunset" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_deprecation_sunset.id
  }

  config = {
    status_code  = 410
    content_type = "application/json"
    body = jsonencode({
      message            = "API v1 has passed its sunset date and is no longer available."
      successor_version  = "/orders/deprecation/v2"
      deprecation_policy = "orders-v1-sunset"
    })
  }
}
