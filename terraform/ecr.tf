# ECR Repository

resource "aws_ecr_repository" "ecko" {
  name                 = var.project_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false # Deshabilitado para ahorrar costos
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

# Política de lifecycle para limpiar imágenes antiguas (opcional)
resource "aws_ecr_lifecycle_policy" "ecko" {
  repository = aws_ecr_repository.ecko.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Mantener solo las últimas 5 imágenes"
        selection = {
          tagStatus     = "any"
          countType     = "imageCountMoreThan"
          countNumber   = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

