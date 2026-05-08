variable "konnect_token" {
  description = "Konnect personal access token"
  type        = string
  sensitive   = true
  default     = null
}

variable "konnect_server_url" {
  description = "Konnect API base URL"
  type        = string
  default     = "https://us.api.konghq.com"
}

variable "konnect_control_plane_id" {
  description = "Existing Konnect control plane UUID"
  type        = string
}

variable "azure_ad_tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
  default     = null
}

variable "azure_ad_audience" {
  description = "Azure AD protected API audience"
  type        = string
  default     = null
}

variable "azure_ad_consumer1_client_id" {
  description = "Azure AD consumer 1 app client ID"
  type        = string
  default     = null
}

variable "azure_ad_consumer2_client_id" {
  description = "Azure AD consumer 2 app client ID"
  type        = string
  default     = null
}

variable "keycloak_realm" {
  description = "Local Keycloak realm"
  type        = string
  default     = "kong-demo"
}

variable "keycloak_allowed_role" {
  description = "Role required for Keycloak protected API access"
  type        = string
  default     = "api-access"
}
