variable "netid" {
  description = "Queen's netID — used to prefix all AWS resources"
  type        = string
  default     = "25nsfb"
}

variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ca-central-1"
}

variable "key_pair_name" {
  description = "Name of the AWS key pair for SSH access to EC2"
  type        = string
  default     = "25nsfb-keypair-ca-v3"
}
