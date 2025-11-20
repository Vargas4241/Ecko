# Ecko - Asistente Virtual
# Infraestructura como Código con Terraform
# Despliegue en AWS ECS Fargate

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend opcional - puedes usar S3 para state remoto
  # backend "s3" {
  #   bucket = "ecko-terraform-state"
  #   key    = "terraform.tfstate"
  #   region = "us-east-1"
  # }
}

# Provider AWS
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Ecko"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

