# Variables de configuración para Terraform

variable "aws_region" {
  description = "Región de AWS donde se desplegarán los recursos"
  type        = string
  default     = "us-east-1" # Cambia a la región que prefieras
}

variable "environment" {
  description = "Ambiente de despliegue (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nombre del proyecto"
  type        = string
  default     = "ecko"
}

variable "app_name" {
  description = "Nombre de la aplicación"
  type        = string
  default     = "ecko-asistente"
}

# ECS Fargate Configuration
variable "ecs_task_cpu" {
  description = "CPU units para el task de ECS Fargate (256 = 0.25 vCPU)"
  type        = number
  default     = 256 # Free Tier friendly
}

variable "ecs_task_memory" {
  description = "Memoria (MB) para el task de ECS Fargate"
  type        = number
  default     = 512 # Free Tier friendly
}

variable "desired_count" {
  description = "Número deseado de tareas de ECS"
  type        = number
  default     = 1 # Empezar con 1 para ahorrar costos
}

# Container Configuration
variable "container_port" {
  description = "Puerto del contenedor"
  type        = number
  default     = 8000
}

variable "container_image" {
  description = "URL de la imagen del contenedor en ECR"
  type        = string
  default     = "" # Se actualizará después de push a ECR
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block para la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zonas de disponibilidad"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# ALB Configuration (opcional - aumenta costos)
variable "enable_alb" {
  description = "Habilitar Application Load Balancer (aumenta costos ~$16/mes)"
  type        = bool
  default     = false # Deshabilitado para empezar con Free Tier
}

# Environment variables para el contenedor
variable "env_vars" {
  description = "Variables de entorno para el contenedor"
  type = map(string)
  default = {
    PYTHONUNBUFFERED = "1"
    PORT            = "8000"
  }
}

# Secrets (usar AWS Secrets Manager o Systems Manager Parameter Store en producción)
variable "groq_api_key" {
  description = "API Key de Groq (usar AWS Secrets Manager en producción)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "use_ai" {
  description = "Habilitar IA (true/false)"
  type        = string
  default     = "true"
}

