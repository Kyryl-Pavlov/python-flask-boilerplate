locals {
  prefix = "${var.app_name}-${var.environment}"
}

resource "aws_wafv2_web_acl" "main" {
  name  = local.prefix
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  # 1 — Block known bad inputs (log4j, path traversal, etc.)
  rule {
    name     = "KnownBadInputs"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefix}-known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  # 2 — OWASP Top 10 (XSS, SQLi, etc.) — note: SQLi is also covered by rule 3
  rule {
    name     = "CommonRules"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"

        # SizeRestrictions_BODY blocks any body > 8 KB, which breaks file uploads.
        # Flask enforces MAX_CONTENT_LENGTH = 50 MB, so WAF's check is redundant here.
        rule_action_override {
          name = "SizeRestrictions_BODY"
          action_to_use {
            count {}
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefix}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # 3 — SQL injection protection
  rule {
    name     = "SQLiProtection"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefix}-sqli"
      sampled_requests_enabled   = true
    }
  }

  # 4 — Per-IP rate limit (DDoS / brute-force mitigation)
  rule {
    name     = "RateLimit"
    priority = 4

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.prefix}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = local.prefix
    sampled_requests_enabled   = true
  }
}

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# WAF log group name must start with "aws-waf-logs-" — AWS requirement.
resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-${local.prefix}"
  retention_in_days = 90
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn
}
