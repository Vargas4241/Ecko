# Outputs de Terraform

output "ecs_cluster_name" {
  description = "Nombre del ECS Cluster"
  value       = aws_ecs_cluster.ecko.name
}

output "ecs_service_name" {
  description = "Nombre del ECS Service"
  value       = aws_ecs_service.ecko.name
}

output "ecr_repository_url" {
  description = "URL del repositorio ECR"
  value       = aws_ecr_repository.ecko.repository_url
}

output "task_definition_arn" {
  description = "ARN de la Task Definition"
  value       = aws_ecs_task_definition.ecko.arn
}

output "cloudwatch_log_group" {
  description = "Grupo de logs de CloudWatch"
  value       = aws_cloudwatch_log_group.ecko.name
}

# Outputs condicionales para ALB
output "alb_dns_name" {
  description = "DNS name del Application Load Balancer"
  value       = var.enable_alb ? aws_lb.ecko[0].dns_name : "ALB deshabilitado"
}

output "alb_target_group_arn" {
  description = "ARN del Target Group del ALB"
  value       = var.enable_alb ? aws_lb_target_group.ecko[0].arn : "ALB deshabilitado"
}

# URL de acceso a la aplicación
output "app_url" {
  description = "URL para acceder a la aplicación"
  value = var.enable_alb ? "http://${aws_lb.ecko[0].dns_name}" : "Usa la IP pública de la tarea de ECS"
}

output "vpc_id" {
  description = "ID de la VPC"
  value       = aws_vpc.ecko.id
}

output "public_subnet_ids" {
  description = "IDs de las subnets públicas"
  value       = aws_subnet.public[*].id
}

# Instrucciones para push de imagen
output "docker_login_command" {
  description = "Comando para hacer login en ECR"
  value       = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.ecko.repository_url}"
}

output "docker_push_command" {
  description = "Comando para pushear imagen a ECR"
  value       = "docker tag ecko-ecko:latest ${aws_ecr_repository.ecko.repository_url}:latest && docker push ${aws_ecr_repository.ecko.repository_url}:latest"
}

