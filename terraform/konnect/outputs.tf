output "control_plane_id" {
  value = var.konnect_control_plane_id
}

output "header_routing_services" {
  value = [
    konnect_gateway_service.svc_orders_header_east.name,
    konnect_gateway_service.svc_orders_header_west.name,
    konnect_gateway_service.svc_orders_header_missing_region.name,
  ]
}

output "rate_limiting_services" {
  value = [
    konnect_gateway_service.svc_orders_rate_anonymous.name,
    konnect_gateway_service.svc_orders_rate_consumer.name,
  ]
}
