terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.48.0"
    }
  }
  required_version = "~> 1.0"
}

variable "region" {
  default = "eu-west-1"
}

provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

locals {
  account_id          = data.aws_caller_identity.current.account_id
}


resource "aws_dynamodb_table" "river_levels_table" {
  name           = "river_levels"
  billing_mode   = "PROVISIONED"
  read_capacity  = 5
  write_capacity = 5
  hash_key       = "river_name"
  range_key      = "timestamp"

  attribute {
    name = "river_name"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }
}

resource "aws_cloudwatch_event_rule" "every_five_minutes" {
  name                = "every-five-minutes"
  description         = "Fires every five minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_rule" "every_sixty_minutes" {
  name                = "every_sixty_minutes"
  description         = "Fires every every_sixty_minutes"
  schedule_expression = "rate(60 minutes)"
}

//----------------------------------------------------------------------------------------------------
// get epa lambda and its need iam and cloudwatch stuff

module "get_epa_lambda" {
  source = "./tf_mod/docker_python_lambda"
  account_id = local.account_id
  name = "get_epa_lambda"
  app_dir = "APP_epa_gauges_fetcher"
  timeout = 30
  memory_size = 512
}

resource "aws_iam_role_policy" "iam_for_dynamo_write" {
  name   = "iam_for_lambda_update_levels_table_dyanmo"
  role   = module.get_epa_lambda.iam_name
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement":[{
    "Effect": "Allow",
    "Action": [
     "dynamodb:BatchGetItem",
     "dynamodb:GetItem",
     "dynamodb:Query",
     "dynamodb:Scan",
     "dynamodb:BatchWriteItem",
     "dynamodb:PutItem",
     "dynamodb:UpdateItem"
    ],
    "Resource": "${aws_dynamodb_table.river_levels_table.arn}"
   }
  ]
}
EOF
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = module.get_epa_lambda.id
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_five_minutes.arn
}

resource "aws_cloudwatch_event_target" "check_level_every_five_minutes" {
  rule      = aws_cloudwatch_event_rule.every_five_minutes.name
  target_id = module.get_epa_lambda.id
  arn       = module.get_epa_lambda.arn
  input     = "{\"current\":[\"current\"]}"
}

resource "aws_cloudwatch_event_target" "update_past_level_every_hour" {
  rule      = aws_cloudwatch_event_rule.every_five_minutes.name
  target_id = module.get_epa_lambda.id
  arn       = module.get_epa_lambda.arn
  input     = "{\"past\":[\"past\"]}"
}

//----------------------------------------------------------------------------------------------------
// get ni lambda and its need iam and cloudwatch stuff

module "get_ni_lambda" {
  source = "./tf_mod/docker_python_lambda"
  account_id = local.account_id
  name = "get_ni_lambda"
  app_dir = "APP_ni_gauges_fetcher"
  timeout = "30"
}

resource "aws_iam_role_policy" "iam_for_dynamo_write_ni" {
  name   = "iam_for_${module.get_ni_lambda.iam_name}"
  role   = module.get_ni_lambda.iam_name
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement":[{
    "Effect": "Allow",
    "Action": [
     "dynamodb:BatchGetItem",
     "dynamodb:GetItem",
     "dynamodb:Query",
     "dynamodb:Scan",
     "dynamodb:BatchWriteItem",
     "dynamodb:PutItem",
     "dynamodb:UpdateItem"
    ],
    "Resource": "${aws_dynamodb_table.river_levels_table.arn}"
   }
  ]
}
EOF
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_ni_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = module.get_ni_lambda.id
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_five_minutes.arn
}

resource "aws_cloudwatch_event_target" "check_ni_level_every_five_minutes" {
  rule      = aws_cloudwatch_event_rule.every_five_minutes.name
  target_id = module.get_ni_lambda.id
  arn       = module.get_ni_lambda.arn
  input     = "{\"current\":[\"current\"]}"
}

//----------------------------------------------------------------------------------------------------
// get ni lambda and its need iam and cloudwatch stuff

module "get_opw_lambda" {
  source = "./tf_mod/docker_python_lambda"
  account_id = local.account_id
  name = "get_opw_lambda"
  app_dir = "APP_opw_gauges_fetcher"
  timeout = "30"
}

resource "aws_iam_role_policy" "iam_for_dynamo_write_opw" {
  name   = "iam_for_${module.get_opw_lambda.iam_name}"
  role   = module.get_opw_lambda.iam_name
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement":[{
    "Effect": "Allow",
    "Action": [
     "dynamodb:BatchGetItem",
     "dynamodb:GetItem",
     "dynamodb:Query",
     "dynamodb:Scan",
     "dynamodb:BatchWriteItem",
     "dynamodb:PutItem",
     "dynamodb:UpdateItem"
    ],
    "Resource": "${aws_dynamodb_table.river_levels_table.arn}"
   }
  ]
}
EOF
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_opw_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = module.get_opw_lambda.id
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_sixty_minutes.arn
}

resource "aws_cloudwatch_event_target" "check_opw_level_every_sixty_minutes" {
  rule      = aws_cloudwatch_event_rule.every_sixty_minutes.name
  target_id = module.get_opw_lambda.id
  arn       = module.get_opw_lambda.arn
  input     = "{\"current\":[\"current\"]}"
}

//----------------------------------------------------------------------------------------------------
// build website lambda and its need iam and cloudwatch stuff

module "build_website_lambda" {
  source = "./tf_mod/docker_python_lambda"
  account_id = local.account_id
  name = "build_webpage_lambda"
  app_dir = "APP_build_website"
  timeout = "30"
  memory_size = "512"
}

resource "aws_iam_role_policy" "iam_for_dynamo_build_website" {
  name   = "iam_for_${module.get_ni_lambda.iam_name}"
  role   = module.build_website_lambda.iam_name
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement":[{
    "Effect": "Allow",
    "Action": [
     "dynamodb:BatchGetItem",
     "dynamodb:GetItem",
     "dynamodb:Query",
     "dynamodb:Scan",
     "dynamodb:BatchWriteItem",
     "dynamodb:PutItem",
     "dynamodb:UpdateItem"
    ],
    "Resource": "${aws_dynamodb_table.river_levels_table.arn}"
   }
  ]
}
EOF
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_build_website" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = module.build_website_lambda.id
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_five_minutes.arn
}

resource "aws_cloudwatch_event_target" "build_website_every_five_minutes" {
  rule      = aws_cloudwatch_event_rule.every_five_minutes.name
  target_id = module.build_website_lambda.id
  arn       = module.build_website_lambda.arn
  input     = "{\"current\":[\"current\"]}"
}

resource "aws_secretsmanager_secret" "scp_key" {
  name = "scp_key"
}

resource "aws_secretsmanager_secret_version" "example" {
  secret_id     = aws_secretsmanager_secret.scp_key.id
  secret_string = var.PW
}

variable "PW" {
  type = string
}

resource "aws_iam_role_policy" "iam_for_secrete_build_web" {
  name   = "iam_for_${module.build_website_lambda.iam_name}"
  role   = module.build_website_lambda.iam_name
  policy = <<EOF
{
  "Version": "2012-10-17",
"Statement": [
        {
            "Effect": "Allow",
            "Action": [
              "secretsmanager:GetSecretValue",
              "secretsmanager:DescribeSecret",
              "secretsmanager:ListSecretVersionIds",
              "secretsmanager:PutSecretValue",
              "secretsmanager:UpdateSecret",
              "secretsmanager:TagResource",
              "secretsmanager:UntagResource"
            ],
            "Resource": [
              "${aws_secretsmanager_secret.scp_key.arn}"
            ]
        }
    ]
}
EOF
}
