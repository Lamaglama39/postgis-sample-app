data "http" "ipv4_icanhazip" {
  url = "http://ipv4.icanhazip.com/"
}

locals {
  app_name     = "nearest-world-heritage-site"
  current_ip   = chomp(data.http.ipv4_icanhazip.response_body)
  allowed_cidr = "${local.current_ip}/32"
}
