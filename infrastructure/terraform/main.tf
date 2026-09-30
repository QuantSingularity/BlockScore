terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "blockscore-terraform-state"
    key            = "blockscore/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.default_tags
  }
}

# Separate provider for us-east-1 - WAF for CloudFront must be in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = var.default_tags
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "network" {
  source = "./modules/network"

  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  project_name         = var.app_name
}

module "security" {
  source = "./modules/security"

  environment  = var.environment
  vpc_id       = module.network.vpc_id
  project_name = var.app_name
}

module "waf" {
  source = "./modules/waf"

  providers = {
    aws = aws.us_east_1
  }

  environment  = var.environment
  project_name = var.app_name
}

module "compute" {
  source = "./modules/compute"

  environment               = var.environment
  vpc_id                    = module.network.vpc_id
  subnet_ids                = module.network.private_subnet_ids
  public_subnet_ids         = module.network.public_subnet_ids
  instance_type             = var.instance_type
  key_name                  = var.key_name
  project_name              = var.app_name
  security_group_ids        = [module.security.app_security_group_id]
  iam_instance_profile_name = module.security.instance_profile_name
  kms_key_arn               = module.security.kms_key_arn
  acm_certificate_arn       = var.acm_certificate_arn
  min_size                  = var.asg_min_size
  max_size                  = var.asg_max_size
  desired_capacity          = var.asg_desired_capacity
}

module "database" {
  source = "./modules/database"

  environment             = var.environment
  vpc_id                  = module.network.vpc_id
  private_subnet_ids      = module.network.private_subnet_ids
  db_instance_class       = var.db_instance_class
  db_name                 = var.db_name
  db_username             = var.db_username
  db_password             = var.db_password
  security_group_ids      = [module.security.db_security_group_id]
  project_name            = var.app_name
  kms_key_arn             = module.security.kms_key_arn
  monitoring_role_arn     = module.security.rds_monitoring_role_arn
  allocated_storage       = var.db_allocated_storage
  backup_retention_period = var.environment == "prod" ? 30 : 7
}

module "storage" {
  source = "./modules/storage"

  environment  = var.environment
  app_name     = var.app_name
  project_name = var.app_name
}

module "logging" {
  source = "./modules/logging"

  environment  = var.environment
  project_name = var.app_name
  aws_region   = var.aws_region
}

module "secrets" {
  source = "./modules/secrets"

  environment  = var.environment
  project_name = var.app_name
  db_username  = var.db_username
  db_password  = var.db_password
}

module "cdn" {
  source = "./modules/cdn"

  providers = {
    aws = aws.us_east_1
  }

  environment        = var.environment
  project_name       = var.app_name
  origin_domain_name = module.compute.alb_dns_name
  origin_type        = "custom"
  web_acl_arn        = module.waf.web_acl_arn
}
