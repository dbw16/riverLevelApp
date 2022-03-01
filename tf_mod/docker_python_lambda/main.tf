// This module will...

// Requirements to run:
// Docker, needed to create the docker container.
// The python (suppose dosnt have to be python) app must be in project_xxxx_dir/app/

//What do we need for this to work?
//ecr
//iam
//the lambdas

locals {
    ecr_image_tag       = "latest"
}

resource "aws_ecr_repository" "repo" {
  name = var.name
}

resource "aws_ecr_lifecycle_policy" "only_lastest_image_policy" {
  repository = aws_ecr_repository.repo.id

  policy = <<EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Rule 1",
            "selection": {
                "tagStatus": "any",
                "countType": "imageCountMoreThan",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
}


resource "null_resource" "ecr_image" {
  triggers = {
    python_file = md5(file("${var.app_dir}/main.py"))  # could trigger on more files
    docker_file = md5(file("${var.app_dir}/Dockerfile"))
  }

  provisioner "local-exec" {
    command = <<EOF
           aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin ${var.account_id}.dkr.ecr.${var.region}.amazonaws.com
           cd ${var.app_dir}
           docker build -t ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag} .
           docker push ${aws_ecr_repository.repo.repository_url}:${local.ecr_image_tag}
       EOF
  }
}

data "aws_ecr_image" "lambda_image" {
  depends_on = [
    null_resource.ecr_image
  ]
  repository_name = var.name
  image_tag       = local.ecr_image_tag

}

resource "aws_lambda_function" "lambda_update_levels_table" {
  function_name = var.name
  role          = aws_iam_role.iam_for_lambda.arn
  depends_on    = [null_resource.ecr_image]
  timeout       = var.timeout
  image_uri     = "${aws_ecr_repository.repo.repository_url}@${data.aws_ecr_image.lambda_image.id}"
  package_type  = "Image"
  memory_size = var.memory_size
}


resource "aws_iam_role" "iam_for_lambda" {
  name = "${var.name}_iam_role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}