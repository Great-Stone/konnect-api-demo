resource "konnect_gateway_service" "svc_orders_ip_restriction" {
  name             = "svc-orders-ip-restriction"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_ip_restriction" {
  name             = "route-orders-ip-restriction"
  methods          = ["GET"]
  paths            = ["/orders/network/ip"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_ip_restriction.id
  }
}

resource "konnect_gateway_plugin_ip_restriction" "orders_ip_restriction" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_ip_restriction.id
  }

  config = {
    allow = ["10.10.10.0/24"]
    deny  = ["10.10.10.66"]
  }
}

resource "konnect_gateway_service" "svc_orders_schema_validation" {
  name             = "svc-orders-schema-validation"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_schema_validation" {
  name             = "route-orders-schema-validation"
  methods          = ["POST"]
  paths            = ["/orders/validate/schema"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_schema_validation.id
  }
}

resource "konnect_gateway_plugin_request_validator" "orders_schema_validation" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_schema_validation.id
  }

  config = {
    version               = "kong"
    allowed_content_types = ["application/json"]
    body_schema = jsonencode([
      {
        orderId = {
          type     = "string"
          required = true
          len_min  = 1
        }
      },
      {
        amount = {
          type     = "number"
          required = true
        }
      },
      {
        currency = {
          type     = "string"
          required = true
          one_of   = ["USD", "INR"]
        }
      }
    ])
    parameter_schema = [
      {
        name     = "channel"
        in       = "query"
        required = true
        schema   = jsonencode({ type = "string", enum = ["web", "mobile"] })
        style    = "form"
        explode  = true
      },
      {
        name     = "x-order-source"
        in       = "header"
        required = true
        schema   = jsonencode({ type = "string", enum = ["portal", "partner"] })
        style    = "simple"
        explode  = false
      }
    ]
  }
}

resource "konnect_gateway_service" "svc_orders_request_size" {
  name             = "svc-orders-request-size"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_request_size" {
  name             = "route-orders-request-size"
  methods          = ["POST"]
  paths            = ["/orders/limits/request-size"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_request_size.id
  }
}

resource "konnect_gateway_plugin_request_size_limiting" "orders_request_size" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_request_size.id
  }

  config = {
    allowed_payload_size = 2
    size_unit            = "kilobytes"
  }
}

resource "konnect_gateway_service" "svc_orders_injection_protection" {
  name             = "svc-orders-injection-protection"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_injection_query" {
  name             = "route-orders-injection-query"
  methods          = ["GET"]
  paths            = ["/orders/security/injection/query"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_injection_protection.id
  }
}

resource "konnect_gateway_plugin_injection_protection" "orders_injection_query" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_injection_query.id
  }

  config = {
    injection_types   = ["sql"]
    locations         = ["path_and_query"]
    enforcement_mode  = "block"
    error_status_code = 400
    error_message     = "Bad Request"
  }
}

resource "konnect_gateway_route" "route_orders_injection_body" {
  name             = "route-orders-injection-body"
  methods          = ["POST"]
  paths            = ["/orders/security/injection/body"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_injection_protection.id
  }
}

resource "konnect_gateway_plugin_injection_protection" "orders_injection_body" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_injection_body.id
  }

  config = {
    injection_types   = ["sql"]
    locations         = ["body"]
    enforcement_mode  = "block"
    error_status_code = 400
    error_message     = "Bad Request"
  }
}

resource "konnect_gateway_route" "route_orders_injection_headers" {
  name             = "route-orders-injection-headers"
  methods          = ["GET"]
  paths            = ["/orders/security/injection/headers"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_injection_protection.id
  }
}

resource "konnect_gateway_plugin_injection_protection" "orders_injection_headers" {
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_injection_headers.id
  }

  config = {
    injection_types   = ["sql"]
    locations         = ["headers"]
    enforcement_mode  = "block"
    error_status_code = 400
    error_message     = "Bad Request"
  }
}
