resource "aws_db_subnet_group" "postgres_subnet_group" {
  name       = "postgres-subnet-group"
  subnet_ids = [aws_subnet.private_subnet_1.id, aws_subnet.private_subnet_2.id]

  tags = {
    Name = "${local.app_name}-subnet-group"
  }
}

resource "aws_db_parameter_group" "postgres_param_group" {
  name   = "postgres-param-group"
  family = "postgres17"

  tags = {
    Name = "${local.app_name}-pg"
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "${local.app_name}-rds"
  engine            = "postgres"
  engine_version    = "17.4"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.master_db_name
  username = var.master_db_username
  password = var.master_db_password

  db_subnet_group_name   = aws_db_subnet_group.postgres_subnet_group.name
  vpc_security_group_ids = [aws_security_group.postgres_sg.id]
  parameter_group_name   = aws_db_parameter_group.postgres_param_group.name

  publicly_accessible = false
  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name = "PostgreSQL with PostGIS"
  }
}

output "connection_command" {
  description = "Command to connect to PostgreSQL"
  value       = "psql -h ${aws_db_instance.postgres.address} -U ${var.master_db_username} -d ${var.master_db_name}"
}
