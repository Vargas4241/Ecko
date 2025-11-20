# Application Load Balancer (Opcional - aumenta costos)

# ALB
resource "aws_lb" "ecko" {
  count              = var.enable_alb ? 1 : 0
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb[0].id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false # Cambiar a true en producción

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "ecko" {
  count       = var.enable_alb ? 1 : 0
  name        = "${var.project_name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.ecko.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
    protocol            = "HTTP"
  }

  tags = {
    Name = "${var.project_name}-target-group"
  }
}

# Listener HTTP (redirige a HTTPS en producción)
resource "aws_lb_listener" "ecko" {
  count             = var.enable_alb ? 1 : 0
  load_balancer_arn = aws_lb.ecko[0].arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ecko[0].arn
  }

  tags = {
    Name = "${var.project_name}-listener"
  }
}

# TODO: Agregar listener HTTPS en producción con certificado SSL

