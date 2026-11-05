terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"

  default_tags {
    tags = {
      Project     = "aws-learning"
      Environment = "bootstrap"
    }
  }
}

# 1. S3 Bucket for Terraform Remote State Storage
resource "aws_s3_bucket" "state" {
  bucket        = "wp-lab-tfstate-538820337783"
  force_destroy = false # Protects state file from accidental destruction

  tags = {
    Name = "wp-lab-tfstate-538820337783"
  }
}

# 2. Enable S3 Bucket Versioning (Instant Disaster Recovery & Rollback)
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# 3. Enable Server-Side Encryption at Rest (SSE-S3 / AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 4. Block All Public Access (Zero-Trust Private State Storage)
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 5. DynamoDB Table for Distributed State Locking (Concurrency Protection)
resource "aws_dynamodb_table" "locks" {
  name         = "wp-lab-tf-locks"
  billing_mode = "PAY_PER_REQUEST" # On-demand, AWS Free Tier friendly
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "wp-lab-tf-locks"
  }
}

# Outputs for Verification
output "s3_bucket_name" {
  description = "Remote state S3 bucket name"
  value       = aws_s3_bucket.state.id
}

output "dynamodb_table_name" {
  description = "DynamoDB state locking table name"
  value       = aws_dynamodb_table.locks.name
}

