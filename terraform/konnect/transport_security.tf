resource "konnect_gateway_service" "svc_orders_transport_security" {
  name             = "svc-orders-transport-security"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_http_blocked" {
  name                       = "route-orders-http-blocked"
  methods                    = ["GET"]
  paths                      = ["/orders/transport/http-blocked"]
  protocols                  = ["https"]
  https_redirect_status_code = 426
  strip_path                 = false
  control_plane_id           = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_transport_security.id
  }
}

resource "konnect_gateway_route" "route_orders_http_redirect" {
  name                       = "route-orders-http-redirect"
  methods                    = ["GET"]
  paths                      = ["/orders/transport/http-redirect"]
  protocols                  = ["https"]
  https_redirect_status_code = 308
  strip_path                 = false
  control_plane_id           = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_transport_security.id
  }
}
