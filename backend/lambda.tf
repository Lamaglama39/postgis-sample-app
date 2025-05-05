
resource "aws_iam_role" "lambda_role" {
  name = "${local.app_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_vpc_access" {
  name = "${local.app_name}-lambda-vpc-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambdaレイヤー
resource "aws_lambda_layer_version" "psycopg2_layer" {
  layer_name          = "psycopg2-binary-3-12"
  filename            = "lambda/psycopg2-3.12.zip"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("lambda/psycopg2-3.12.zip")
}

resource "aws_lambda_function" "db_handler" {
  filename      = "lambda/db_handler.zip"
  function_name = "${local.app_name}-db-handler"
  role          = aws_iam_role.lambda_role.arn
  handler       = "db_handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  layers = [
    aws_lambda_layer_version.psycopg2_layer.arn
  ]

  environment {
    variables = {
      DB_HOST     = aws_db_instance.postgres.address
      DB_NAME     = var.postgis_db_name
      DB_USER     = var.postgis_db_username
      DB_PASSWORD = var.postgis_db_password
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_vpc_access,
    aws_lambda_layer_version.psycopg2_layer
  ]
}

resource "aws_lambda_function_url" "db_handler_url" {
  function_name      = aws_lambda_function.db_handler.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = true
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["*"]
    max_age           = 3600
  }
}

output "lambda_url" {
  value = aws_lambda_function_url.db_handler_url.function_url
}

resource "aws_lambda_function" "rds_setup" {
  filename      = "lambda/rds_setup.zip"
  function_name = "${local.app_name}-rds-setup"
  role          = aws_iam_role.lambda_role.arn
  handler       = "rds_setup.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  layers = [
    aws_lambda_layer_version.psycopg2_layer.arn
  ]

  environment {
    variables = {
      DB_HOST            = aws_db_instance.postgres.address
      DB_NAME            = var.postgis_db_name
      DB_USER            = var.postgis_db_username
      DB_PASSWORD        = var.postgis_db_password
      MASTER_DB_NAME     = var.master_db_name
      MASTER_DB_USER     = var.master_db_username
      MASTER_DB_PASSWORD = var.master_db_password
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.public_subnet_1.id, aws_subnet.public_subnet_2.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_vpc_access
  ]
}

resource "aws_lambda_function_url" "rds_setup_url" {
  function_name      = aws_lambda_function.rds_setup.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = true
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["*"]
    max_age           = 3600
  }
}

output "rds_setup_url" {
  value = aws_lambda_function_url.rds_setup_url.function_url
}
