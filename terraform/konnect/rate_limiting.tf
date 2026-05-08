resource "konnect_gateway_service" "svc_orders_rate_anonymous" {
  name             = "svc-orders-rate-anonymous"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_rate_anonymous" {
  name             = "route-orders-rate-anonymous"
  methods          = ["GET"]
  paths            = ["/orders/rate/anonymous"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_rate_anonymous.id
  }
}

resource "konnect_gateway_plugin_rate_limiting_advanced" "rate_limit_anonymous" {
  control_plane_id = var.konnect_control_plane_id
  service = {
    id = konnect_gateway_service.svc_orders_rate_anonymous.id
  }

  config = {
    limit               = [20]
    window_size         = [30]
    window_type         = "fixed"
    strategy            = "local"
    identifier          = "ip"
    hide_client_headers = false
  }

  lifecycle {
    ignore_changes = [config["namespace"], config["redis"]]
  }
}

resource "konnect_gateway_service" "svc_orders_rate_consumer" {
  name             = "svc-orders-rate-consumer"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_rate_consumer" {
  name             = "route-orders-rate-consumer"
  methods          = ["GET"]
  paths            = ["/orders/rate/consumer"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_rate_consumer.id
  }
}

resource "konnect_gateway_plugin_key_auth" "key_auth_orders_rate_consumer" {
  control_plane_id = var.konnect_control_plane_id
  service = {
    id = konnect_gateway_service.svc_orders_rate_consumer.id
  }

  config = {
    key_names        = ["apikey"]
    hide_credentials = false
  }
}

resource "konnect_gateway_consumer" "consumer_gold" {
  username         = "consumer-gold"
  custom_id        = "consumer-gold"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_gold_key" {
  key              = "key-consumer-gold"
  consumer_id      = konnect_gateway_consumer.consumer_gold.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_plugin_rate_limiting_advanced" "rate_limit_consumer_gold" {
  control_plane_id = var.konnect_control_plane_id
  consumer = {
    id = konnect_gateway_consumer.consumer_gold.id
  }

  config = {
    limit               = [10]
    window_size         = [30]
    window_type         = "fixed"
    strategy            = "local"
    identifier          = "consumer"
    hide_client_headers = false
  }

  lifecycle {
    ignore_changes = [config["namespace"], config["redis"]]
  }
}

resource "konnect_gateway_consumer" "consumer_standard" {
  username         = "consumer-standard"
  custom_id        = "consumer-standard"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_standard_key" {
  key              = "key-consumer-standard"
  consumer_id      = konnect_gateway_consumer.consumer_standard.id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_plugin_rate_limiting_advanced" "rate_limit_consumer_standard" {
  control_plane_id = var.konnect_control_plane_id
  consumer = {
    id = konnect_gateway_consumer.consumer_standard.id
  }

  config = {
    limit               = [5]
    window_size         = [30]
    window_type         = "fixed"
    strategy            = "local"
    identifier          = "consumer"
    hide_client_headers = false
  }

  lifecycle {
    ignore_changes = [config["namespace"], config["redis"]]
  }
}
