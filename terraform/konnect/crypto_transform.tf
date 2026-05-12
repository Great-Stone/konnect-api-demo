resource "konnect_gateway_service" "svc_orders_payload_crypto" {
  name             = "svc-orders-payload-crypto"
  protocol         = "http"
  host             = "orders-east"
  port             = 9101
  path             = "/"
  control_plane_id = var.konnect_control_plane_id
}

resource "konnect_gateway_route" "route_orders_payload_crypto" {
  name             = "route-orders-payload-crypto"
  methods          = ["POST"]
  paths            = ["/orders/security/payload-crypto"]
  protocols        = ["http", "https"]
  strip_path       = false
  control_plane_id = var.konnect_control_plane_id

  service = {
    id = konnect_gateway_service.svc_orders_payload_crypto.id
  }
}

resource "konnect_gateway_custom_plugin_schema" "payload_crypto_demo" {
  control_plane_id = var.konnect_control_plane_id
  lua_schema       = file("${path.module}/../../kong_plugins/kong/plugins/payload-crypto-demo/schema.lua")
}

resource "konnect_gateway_custom_plugin" "payload_crypto_demo" {
  name             = "payload-crypto-demo"
  enabled          = true
  control_plane_id = var.konnect_control_plane_id
  config = jsonencode({
    algorithm                          = "AES/CBC/PKCS5Padding"
    gateway_private_key_path           = "/crypto/gateway_private.pem"
    client_public_key_path             = "/crypto/client_public.pem"
    gateway_private_key_passphrase_env = "CRYPTO_GATEWAY_PRIVATE_KEY_PASSPHRASE"
  })

  route = {
    id = konnect_gateway_route.route_orders_payload_crypto.id
  }

  depends_on = [
    konnect_gateway_custom_plugin_schema.payload_crypto_demo,
  ]
}
