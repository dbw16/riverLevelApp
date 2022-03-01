# Input variable definitions

variable "name" {
  description = "Name of the lambda function will be used for creating the lambda and the needed ecr repo"
  type        = string
}

variable "app_dir" {
    description = "Directory where the apps python code is"
    type        = string
}

variable "region" {
  description = "Region where the lambda is located"
  default     = "eu-west-1"
}

variable "account_id" {
  description = "account id"
  type        = string
}

variable "timeout" {
  type = number
  default = 30
}

variable "memory_size" {
  type = number
  default = 128
}