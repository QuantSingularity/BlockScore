resource "aws_secretsmanager_secret" "db_credentials" {
  name_prefix = "${var.project_name}-${var.environment}-db-"
  description = "Database credentials for ${var.project_name} ${var.environment}"

  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-credentials"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    engine   = "mysql"
    port     = 3306
  })
}

resource "aws_secretsmanager_secret" "api_keys" {
  name_prefix = "${var.project_name}-${var.environment}-api-"
  description = "API keys for ${var.project_name} ${var.environment}"

  recovery_window_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-keys"
    Environment = var.environment
  }
}
