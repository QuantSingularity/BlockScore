resource "aws_cloudfront_origin_access_control" "main" {
  name                              = "${var.project_name}-${var.environment}-oac"
  description                       = "OAC for ${var.project_name}-${var.environment}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "main" {
  origin {
    domain_name = var.origin_domain_name
    origin_id   = "${var.project_name}-${var.environment}-origin"

    dynamic "s3_origin_config" {
      for_each = var.origin_type == "s3" ? [1] : []
      content {
        origin_access_identity = ""
      }
    }

    dynamic "origin_access_control_id" {
      for_each = var.origin_type == "s3" ? [1] : []
      content {
        value = aws_cloudfront_origin_access_control.main.id
      }
    }

    dynamic "custom_origin_config" {
      for_each = var.origin_type == "custom" ? [1] : []
      content {
        http_port                = 80
        https_port               = 443
        origin_protocol_policy   = "https-only"
        origin_ssl_protocols     = ["TLSv1.2"]
        origin_read_timeout      = 60
        origin_keepalive_timeout = 60
      }
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.project_name}-${var.environment}"
  default_root_object = var.default_root_object

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${var.project_name}-${var.environment}-origin"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # Cache behavior for API endpoints - bypass cache
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "${var.project_name}-${var.environment}-origin"

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "CloudFront-Forwarded-Proto", "Origin", "Accept"]

      cookies {
        forward = "all"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
    viewer_protocol_policy = "https-only"
  }

  price_class = var.price_class

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = var.custom_ssl_certificate_arn == null ? true : false
    acm_certificate_arn            = var.custom_ssl_certificate_arn
    ssl_support_method             = var.custom_ssl_certificate_arn != null ? "sni-only" : null
    minimum_protocol_version       = var.custom_ssl_certificate_arn != null ? "TLSv1.2_2021" : "TLSv1.2_2021"
  }

  web_acl_id = var.web_acl_arn

  tags = {
    Name        = "${var.project_name}-${var.environment}-cloudfront"
    Environment = var.environment
  }
}
