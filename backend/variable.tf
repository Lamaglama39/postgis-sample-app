variable "aws_region" {
  default = "ap-northeast-1"
}

variable "master_db_name" {
  default = "postgisdb"
}

variable "master_db_username" {
  default = "postgres"
}

variable "master_db_password" {
  default = "postgres"
}

variable "postgis_db_name" {
  default = "lab_gis"
}

variable "postgis_db_username" {
  default = "gis_admin"
}

variable "postgis_db_password" {
  default = "gis_admin"
}
