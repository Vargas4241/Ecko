# 🏗️ Terraform - Infraestructura AWS para Ecko

Esta guía te ayudará a desplegar Ecko en AWS usando Terraform.

## 📋 Prerrequisitos

1. **Cuenta de AWS** con Free Tier activo
2. **Terraform instalado** (versión >= 1.0)
   ```bash
   # Windows (con Chocolatey)
   choco install terraform

   # O descarga desde https://www.terraform.io/downloads
   ```
3. **AWS CLI instalado y configurado**
   ```bash
   aws configure
   # Necesitarás: Access Key ID, Secret Access Key, región predeterminada
   ```

## 🚀 Configuración Inicial

### 1. Configurar Variables

Copia el archivo de ejemplo y edítalo:

```bash
cd terraform
copy terraform.tfvars.example terraform.tfvars  # Windows
# o
cp terraform.tfvars.example terraform.tfvars    # Linux/Mac
```

Edita `terraform.tfvars` con tus valores:

```hcl
aws_region     = "us-east-1"  # Cambia a tu región preferida
environment    = "dev"
project_name   = "ecko"

# Para ahorrar costos inicialmente:
enable_alb     = false  # ALB cuesta ~$16/mes
desired_count  = 1
ecs_task_cpu   = 256    # 0.25 vCPU
ecs_task_memory = 512   # 512 MB

# IA Configuration
use_ai       = "true"
groq_api_key = "tu_api_key_aqui"
```

⚠️ **IMPORTANTE**: En producción, usa AWS Secrets Manager para la API key de Groq, no la pongas en `terraform.tfvars`.

### 2. Inicializar Terraform

```bash
cd terraform
terraform init
```

Esto descargará los providers necesarios.

### 3. Revisar Plan

```bash
terraform plan
```

Esto te mostrará qué recursos se van a crear. Revisa cuidadosamente.

### 4. Aplicar Configuración

```bash
terraform apply
```

Confirma con `yes` cuando se te pregunte.

## 📦 Despliegue de la Imagen Docker

### 1. Obtener URL de ECR

Después de `terraform apply`, verás el output `ecr_repository_url`. O búscalo con:

```bash
terraform output ecr_repository_url
```

### 2. Login en ECR

```bash
# Usa el comando que aparece en los outputs
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ECR_REPO_URL>
```

O ejecuta el comando del output:

```bash
terraform output -raw docker_login_command
```

### 3. Construir y Pushear Imagen

```bash
# Construir imagen
docker build -t ecko-ecko:latest .

# Taguear para ECR
docker tag ecko-ecko:latest <ECR_REPO_URL>:latest

# Pushear
docker push <ECR_REPO_URL>:latest
```

O usa el comando del output:

```bash
terraform output -raw docker_push_command
```

### 4. Actualizar Task Definition

Después de pushear la imagen, actualiza la variable `container_image` o simplemente actualiza el servicio:

```bash
# Forzar nueva deployment
aws ecs update-service --cluster ecko-cluster --service ecko-service --force-new-deployment
```

## 🔍 Verificar Despliegue

### Ver Estado de ECS

```bash
aws ecs describe-services --cluster ecko-cluster --services ecko-service
```

### Ver Logs

```bash
# Ver logs en CloudWatch
aws logs tail /ecs/ecko --follow

# O desde la consola de AWS:
# CloudWatch > Log groups > /ecs/ecko
```

### Obtener URL de Acceso

Si ALB está habilitado:

```bash
terraform output alb_dns_name
```

Si ALB está deshabilitado:

```bash
# Obtener IP pública de la tarea
aws ecs describe-tasks --cluster ecko-cluster --tasks <TASK_ID>
```

## 🏗️ Estructura de Archivos

```
terraform/
├── main.tf              # Configuración principal y providers
├── variables.tf         # Variables de configuración
├── outputs.tf           # Outputs útiles
├── vpc.tf               # VPC, subnets, security groups
├── ecs.tf               # ECS Cluster, Task Definition, Service
├── ecr.tf               # ECR Repository
├── alb.tf               # Application Load Balancer (opcional)
├── iam.tf               # IAM Roles y Policies
├── terraform.tfvars     # Tus valores (no subir a Git)
└── .gitignore          # Archivos a ignorar
```

## 💰 Estimación de Costos (Free Tier)

### Recursos Gratuitos (primer año):

- ✅ ECS Fargate: 20 GB horas/mes
- ✅ ECR: 500 MB almacenamiento/mes
- ✅ CloudWatch Logs: 5 GB ingest, 5 GB almacenamiento/mes
- ✅ VPC: Gratis
- ✅ Data Transfer: 1 GB/mes fuera de AWS

### Costos Adicionales (estimados):

- ⚠️ **ALB**: ~$16/mes (opcional, deshabilitado por defecto)
- 💰 **ECS Fargate**: 
  - 256 CPU, 512 MB RAM: ~$0.04/hora = ~$30/mes (fuera de Free Tier)
  - Con Free Tier: Primeros 20 GB-horas gratis
- 💰 **Data Transfer**: $0.09/GB después del primer GB

### Cómo Minimizar Costos:

1. **Deshabilita ALB** inicialmente (`enable_alb = false`)
2. **Usa Free Tier** de ECS Fargate (20 GB-horas/mes)
3. **Mantén `desired_count = 1`**
4. **Usa configuraciones mínimas** (256 CPU, 512 MB RAM)
5. **Apaga el servicio** cuando no lo uses (desde AWS Console)

## 🔧 Comandos Útiles

```bash
# Ver estado
terraform show

# Ver outputs
terraform output

# Ver recursos creados
terraform state list

# Destruir infraestructura (⚠️ CUIDADO)
terraform destroy

# Validar configuración
terraform validate

# Formatear código
terraform fmt

# Refrescar estado
terraform refresh
```

## 🔒 Seguridad

### Variables Sensibles

⚠️ **NUNCA** subas `terraform.tfvars` con valores sensibles a Git. Ya está en `.gitignore`.

### Mejores Prácticas para Producción:

1. **Usa AWS Secrets Manager** para API keys:
   ```hcl
   data "aws_secretsmanager_secret_version" "groq_api_key" {
     secret_id = "ecko/groq-api-key"
   }
   ```

2. **Habilita encriptación** en ECR
3. **Usa HTTPS** con certificado SSL en ALB
4. **Restringe Security Groups** a IPs específicas
5. **Usa backend remoto** (S3) para state de Terraform

## 🐛 Troubleshooting

### Error: "No valid credential sources"

```bash
aws configure
```

### Error: "Resource already exists"

Verifica si los recursos ya existen en AWS. Si quieres reusarlos, usa `terraform import`.

### La tarea de ECS no inicia

1. Verifica los logs en CloudWatch
2. Revisa que la imagen esté en ECR
3. Verifica que el Security Group permita tráfico
4. Revisa que el Task Role tenga los permisos necesarios

### No puedo acceder a la aplicación

1. Si ALB está deshabilitado, usa la IP pública de la tarea
2. Verifica Security Groups
3. Verifica que el contenedor esté escuchando en el puerto correcto

## 📚 Recursos Adicionales

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS ECS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [AWS Free Tier](https://aws.amazon.com/free/)

## 🎯 Próximos Pasos

Después de desplegar con Terraform:

1. ✅ Configurar CI/CD (Fase 4)
2. ✅ Auto-scaling básico (Fase 5)
3. ✅ Monitoreo y alertas
4. ✅ Certificado SSL para HTTPS

