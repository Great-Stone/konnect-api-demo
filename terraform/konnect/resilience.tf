resource "konnect_gateway_upstream" "upstream_orders_weighted" {
  name             = "upstream-orders-weighted"
  algorithm        = "round-robin"
  slots            = 10000
  use_srv_name     = false
  control_plane_id = var.konnect_control_plane_id

  healthchecks = {
    active = {
      concurrency = 10
      http_path   = "/health"
      timeout     = 1
      type        = "http"
      healthy = {
        http_statuses = [200]
        interval      = 2
        successes     = 2
      }
      unhealthy = {
        http_failures = 2
        http_statuses = [429, 500, 501, 502, 503, 504, 505]
        interval      = 2
        tcp_failures  = 2
        timeouts      = 2
      }
    }
    passive = {
      type = "http"
      healthy = {
        http_statuses = [200, 201, 202, 203, 204, 205, 206, 207, 208, 226, 300, 301, 302, 303, 304, 305, 306, 307, 308]
        successes     = 0
      }
      unhealthy = {
        http_failures = 2
        http_statuses = [429, 500, 503, 504]
        tcp_failures  = 2
        timeouts      = 2
      }
    }
    threshold = 0
  }
}

resource "konnect_gateway_target" "upstream_orders_weighted_instance_1" {
  target           = "orders-instance-1:9201"
  weight           = 30
  upstream_id      = konnect_gateway_upstream.upstream_orders_weighted.id
  control_plane_id = var.konnect_control_plane_id

  lifecycle {
    ignore_changes = [upstream]
  }
}

resource "konnect_gateway_target" "upstream_orders_weighted_instance_2" {
  target           = "orders-instance-2:9202"
  weight           = 70
  upstream_id      = konnect_gateway_upstream.upstream_orders_weighted.id
  control_plane_id = var.konnect_control_plane_id

  lifecycle {
    ignore_changes = [upstream]
  }
}

resource "konnect_gateway_service" "svc_orders_resilience_weighted" {
  name             = "svc-orders-resilience-weighted"
  protocol         = "http"
  host             = konnect_gateway_upstream.upstream_orders_weighted.name
  port             = 80
  path             = "/"
  retries          = 1
  connect_timeout  = 1000
  read_timeout     = 5000
  write_timeout    = 5000
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_resilience_weighted" {
  name             = "route-orders-resilience-weighted"
  methods          = ["GET"]
  paths            = ["/orders/resilience/weighted"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_resilience_weighted.id
  }
}

resource "konnect_gateway_upstream" "upstream_orders_circuit_breaker" {
  name             = "upstream-orders-circuit-breaker"
  algorithm        = "round-robin"
  slots            = 10000
  use_srv_name     = false
  control_plane_id = var.konnect_control_plane_id

  healthchecks = {
    active = {
      concurrency = 10
      http_path   = "/health"
      timeout     = 1
      type        = "http"
      healthy = {
        http_statuses = [200]
        interval      = 2
        successes     = 2
      }
      unhealthy = {
        http_failures = 2
        http_statuses = [429, 500, 501, 502, 503, 504, 505]
        interval      = 2
        tcp_failures  = 2
        timeouts      = 2
      }
    }
    passive = {
      type = "http"
      healthy = {
        http_statuses = [200, 201, 202, 203, 204, 205, 206, 207, 208, 226, 300, 301, 302, 303, 304, 305, 306, 307, 308]
        successes     = 0
      }
      unhealthy = {
        http_failures = 2
        http_statuses = [429, 500, 503, 504]
        tcp_failures  = 2
        timeouts      = 2
      }
    }
    threshold = 0
  }
}

resource "konnect_gateway_target" "upstream_orders_circuit_breaker_instance_1" {
  target           = "orders-instance-1:9201"
  weight           = 100
  upstream_id      = konnect_gateway_upstream.upstream_orders_circuit_breaker.id
  control_plane_id = var.konnect_control_plane_id

  lifecycle {
    ignore_changes = [upstream]
  }
}

resource "konnect_gateway_target" "upstream_orders_circuit_breaker_instance_2" {
  target           = "orders-instance-2:9202"
  weight           = 100
  upstream_id      = konnect_gateway_upstream.upstream_orders_circuit_breaker.id
  control_plane_id = var.konnect_control_plane_id

  lifecycle {
    ignore_changes = [upstream]
  }
}

resource "konnect_gateway_service" "svc_orders_circuit_breaker" {
  name             = "svc-orders-circuit-breaker"
  protocol         = "http"
  host             = konnect_gateway_upstream.upstream_orders_circuit_breaker.name
  port             = 80
  path             = "/"
  retries          = 1
  connect_timeout  = 1000
  read_timeout     = 5000
  write_timeout    = 5000
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_circuit_breaker" {
  name             = "route-orders-circuit-breaker"
  methods          = ["GET"]
  paths            = ["/orders/resilience/circuit-breaker"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_circuit_breaker.id
  }
}
