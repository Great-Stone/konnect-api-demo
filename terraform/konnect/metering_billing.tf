locals {
  metering_billing_enabled = try(trimspace(var.konnect_system_token), "") != ""
}

resource "konnect_gateway_service" "svc_orders_metering" {
  count            = local.metering_billing_enabled ? 1 : 0
  name             = "svc-orders-metering"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_metering_consumer" {
  count            = local.metering_billing_enabled ? 1 : 0
  name             = "route-orders-metering-consumer"
  methods          = ["GET"]
  paths            = ["/orders/metering/consumer"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_metering[0].id
  }
}

resource "konnect_gateway_consumer" "consumer_metering_bank_1" {
  count            = local.metering_billing_enabled ? 1 : 0
  username         = "demo-bank-1"
  custom_id        = "demo-bank-1"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_consumer" "consumer_metering_bank_2" {
  count            = local.metering_billing_enabled ? 1 : 0
  username         = "demo-bank-2"
  custom_id        = "demo-bank-2"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_metering_bank_1_key" {
  count            = local.metering_billing_enabled ? 1 : 0
  key              = "key-demo-bank-1"
  consumer_id      = konnect_gateway_consumer.consumer_metering_bank_1[0].id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_key_auth" "consumer_metering_bank_2_key" {
  count            = local.metering_billing_enabled ? 1 : 0
  key              = "key-demo-bank-2"
  consumer_id      = konnect_gateway_consumer.consumer_metering_bank_2[0].id
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_plugin_key_auth" "orders_metering_consumer_auth" {
  count            = local.metering_billing_enabled ? 1 : 0
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_metering_consumer[0].id
  }

  config = {
    key_names        = ["apikey"]
    hide_credentials = false
  }
}

resource "konnect_gateway_plugin_metering_and_billing" "orders_metering_consumer" {
  count            = local.metering_billing_enabled ? 1 : 0
  enabled          = true
  control_plane_id = var.konnect_control_plane_id
  route = {
    id = konnect_gateway_route.route_orders_metering_consumer[0].id
  }

  config = {
    ingest_endpoint      = var.konnect_metering_ingest_endpoint
    api_token            = var.konnect_system_token
    meter_api_requests   = true
    meter_ai_token_usage = false
    subject = {
      look_up_value_in = "consumer"
    }
  }

  tags = []
}
