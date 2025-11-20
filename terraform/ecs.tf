# ECS Cluster y Servicios

# ECS Cluster
resource "aws_ecs_cluster" "ecko" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled" # Deshabilitado para ahorrar costos
  }

  tags = {
    Name = "${var.project_name}-cluster"
  }
}

# CloudWatch Log Group para ECS Tasks
resource "aws_cloudwatch_log_group" "ecko" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 7 # Retener logs por 7 días (gratis)

  tags = {
    Name = "${var.project_name}-logs"
  }
}

# Task Definition para ECS Fargate
resource "aws_ecs_task_definition" "ecko" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.ecs_task_cpu
  memory                   = var.ecs_task_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = var.app_name
      image = var.container_image != "" ? var.container_image : "${aws_ecr_repository.ecko.repository_url}:latest"

      portMappings = [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = concat(
        [
          for key, value in var.env_vars : {
            name  = key
            value = value
          }
        ],
        [
          {
            name  = "USE_AI"
            value = var.use_ai
          }
        ],
        var.groq_api_key != "" ? [
          {
            name  = "GROQ_API_KEY"
            value = var.groq_api_key
          }
        ] : []
      )

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecko.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${var.container_port}/health')\""]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      essential = true
    }
  ])

  tags = {
    Name = "${var.project_name}-task-definition"
  }
}

# ECS Service
resource "aws_ecs_service" "ecko" {
  name            = "${var.project_name}-service"
  cluster         = aws_ecs_cluster.ecko.id
  task_definition = aws_ecs_task_definition.ecko.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true # Necesario para que las tareas tengan acceso a internet
  }

  # Configuración de Load Balancer solo si está habilitado
  dynamic "load_balancer" {
    for_each = var.enable_alb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.ecko[0].arn
      container_name   = var.app_name
      container_port   = var.container_port
    }
  }

  # Dependencia implícita: si ALB está habilitado, el load_balancer block crea la dependencia automáticamente
  # No necesitamos depends_on explícito si no hay ALB

  tags = {
    Name = "${var.project_name}-service"
  }
}

