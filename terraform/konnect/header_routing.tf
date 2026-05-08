resource "konnect_gateway_service" "svc_orders_header_east" {
  name             = "svc-orders-header-east"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_header_east" {
  name             = "route-orders-header-east"
  methods          = ["GET"]
  paths            = ["/orders"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id
  headers = {
    x-region = ["east"]
  }

  service = {
    id = konnect_gateway_service.svc_orders_header_east.id
  }
}

resource "konnect_gateway_service" "svc_orders_header_west" {
  name             = "svc-orders-header-west"
  protocol         = "http"
  host             = "orders-west"
  port             = 9102
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_header_west" {
  name             = "route-orders-header-west"
  methods          = ["GET"]
  paths            = ["/orders"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id
  headers = {
    x-region = ["west"]
  }

  service = {
    id = konnect_gateway_service.svc_orders_header_west.id
  }
}

resource "konnect_gateway_service" "svc_orders_header_missing_region" {
  name             = "svc-orders-header-missing-region"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_header_catchall" {
  name             = "route-orders-header-catchall"
  methods          = ["GET"]
  paths            = ["/orders"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_header_missing_region.id
  }
}

resource "konnect_gateway_plugin_request_termination" "orders_header_missing_region_policy" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_header_catchall.id
  }

  config = {
    status_code  = 400
    content_type = "application/json"
    body = jsonencode({
      message        = "Missing required x-region header."
      allowed_values = ["east", "west"]
      policy         = "orders-header-missing-region-policy"
    })
  }
}
