// infra/envs/dev/main.tf
// Environment root for 'dev' — calls the infra root module and passes variables from dev.auto.tfvars

variable "env" {
}
variable "project" {
}
variable "region" {
}

variable "ingestion_zip_path" {
  default = ""
}
variable "compliance_zip_path" {
  default = ""
}

module "root" {
  source = "../../"

  // Core environment details
  env                       = var.env
  project                   = var.project
  region                    = var.region
  ingestion_zip_path       = var.ingestion_zip_path
  compliance_zip_path       = var.compliance_zip_path
}
