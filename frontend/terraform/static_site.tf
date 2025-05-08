resource "aws_s3_bucket" "static_site" {
  bucket        = "${local.app_name}-static-site"
  force_destroy = true

  tags = {
    Name = "${local.app_name}-static-site"
  }
}

resource "aws_s3_bucket_public_access_block" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_website_configuration" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  index_document {
    suffix = "index.html"
  }
  error_document {
    key = "index.html"
  }
}

resource "aws_cloudfront_origin_access_control" "static_site_oac" {
  name                              = "${local.app_name}-oac"
  description                       = "OAC for static site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "static_site" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.static_site.bucket_regional_domain_name
    origin_id                = "s3-static-site"
    origin_access_control_id = aws_cloudfront_origin_access_control.static_site_oac.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "s3-static-site"

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
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "${local.app_name}-cloudfront"
  }
}

resource "aws_s3_bucket_policy" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "cloudfront.amazonaws.com"
        },
        Action   = "s3:GetObject",
        Resource = "${aws_s3_bucket.static_site.arn}/*",
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.static_site.arn
          }
        }
      }
    ]
  })
}

# index.html のアップロード
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.static_site.id
  key          = "index.html"
  source       = "../app/dist/index.html"
  etag         = filemd5("../app/dist/index.html")
  content_type = "text/html"
}

# assetsディレクトリ配下の全ファイルをアップロード
locals {
  asset_files = fileset("../app/dist/assets", "**")
}

resource "aws_s3_object" "assets" {
  for_each = { for file in local.asset_files : file => file }

  bucket = aws_s3_bucket.static_site.id
  key    = "assets/${each.key}"
  source = "../app/dist/assets/${each.key}"
  etag   = filemd5("../app/dist/assets/${each.key}")
  content_type = lookup(
    {
      "js"    = "application/javascript"
      "css"   = "text/css"
      "svg"   = "image/svg+xml"
      "png"   = "image/png"
      "jpg"   = "image/jpeg"
      "jpeg"  = "image/jpeg"
      "woff"  = "font/woff"
      "woff2" = "font/woff2"
      "ttf"   = "font/ttf"
      "map"   = "application/json"
    },
    element(split(".", each.key), length(split(".", each.key)) - 1),
    "application/octet-stream"
  )
}

output "static_site_bucket" {
  value = aws_s3_bucket.static_site.bucket
}

output "cloudfront_url" {
  value = aws_cloudfront_distribution.static_site.domain_name
}
