# VPC y Networking

# VPC Principal
resource "aws_vpc" "ecko" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "ecko" {
  vpc_id = aws_vpc.ecko.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.ecko.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    Type = "Public"
  }
}

# Route Table para Public Subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.ecko.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.ecko.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Route Table Association para Public Subnets
resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Group para ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group para tareas de ECS"
  vpc_id      = aws_vpc.ecko.id

  # Permitir tráfico saliente (necesario para llamadas a APIs externas como Groq)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Si ALB está habilitado, permitir tráfico desde ALB
  # Si no, permitir acceso directo al puerto del contenedor (no recomendado para producción)
  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = var.enable_alb ? [] : ["0.0.0.0/0"]
    description = var.enable_alb ? "Traffic from ALB only" : "Direct access (not recommended for production)"
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

# Security Group para ALB (solo si está habilitado)
resource "aws_security_group" "alb" {
  count       = var.enable_alb ? 1 : 0
  name        = "${var.project_name}-alb-sg"
  description = "Security group para Application Load Balancer"
  vpc_id      = aws_vpc.ecko.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# Permitir tráfico desde ALB hacia ECS Tasks
resource "aws_security_group_rule" "alb_to_ecs" {
  count                    = var.enable_alb ? 1 : 0
  type                     = "ingress"
  from_port                = var.container_port
  to_port                  = var.container_port
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb[0].id
  security_group_id        = aws_security_group.ecs_tasks.id
  description              = "Allow traffic from ALB"
}

