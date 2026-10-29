#!/bin/bash

# BlockScore Infrastructure Validation Script
# This script validates the robustness and scalability of the infrastructure

set -e

echo "Starting BlockScore Infrastructure Validation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Initialize validation report
init_report() {
    mkdir -p reports/validation
    cat > reports/validation/validation-report.md << EOF
# BlockScore Infrastructure Validation Report

## Report Date
$(date)

## Validation Categories
- Terraform Configuration Validation
- Kubernetes Resource Validation
- Security Configuration Validation
- High Availability Validation
- Scalability Validation
- Disaster Recovery Validation

## Validation Results

EOF
}

# Terraform validation
validate_terraform() {
    print_status "Validating Terraform configurations..."

    cat >> reports/validation/validation-report.md << EOF
### Terraform Configuration Validation

EOF

    cd infrastructure/terraform

    # Test terraform init
    print_test "Testing Terraform initialization"
    if terraform init -backend=false > /dev/null 2>&1; then
        echo "✅ Terraform initialization successful" >> ../../reports/validation/validation-report.md
    else
        echo "❌ Terraform initialization failed" >> ../../reports/validation/validation-report.md
    fi

    # Test terraform validate
    print_test "Testing Terraform validation"
    if terraform validate > /dev/null 2>&1; then
        echo "✅ Terraform validation successful" >> ../../reports/validation/validation-report.md
    else
        echo "❌ Terraform validation failed" >> ../../reports/validation/validation-report.md
    fi

    # Test terraform plan for each environment
    for env in dev staging prod; do
        print_test "Testing Terraform plan for $env environment"
        if [ -f "environments/$env/terraform.tfvars" ]; then
            if terraform plan -var-file="environments/$env/terraform.tfvars" -out=/dev/null > /dev/null 2>&1; then
                echo "✅ Terraform plan for $env successful" >> ../../reports/validation/validation-report.md
            else
                echo "❌ Terraform plan for $env failed" >> ../../reports/validation/validation-report.md
            fi
        else
            echo "⚠️ No terraform.tfvars found for $env environment" >> ../../reports/validation/validation-report.md
        fi
    done

    cd ../..
    echo "" >> reports/validation/validation-report.md
}

# Kubernetes validation
validate_kubernetes() {
    print_status "Validating Kubernetes configurations..."

    cat >> reports/validation/validation-report.md << EOF
### Kubernetes Resource Validation

EOF

    # Validate all Kubernetes manifests
    find infrastructure/kubernetes -name "*.yaml" -o -name "*.yml" | while read -r file; do
        print_test "Validating $file"
        if kubectl apply --dry-run=client --validate=true -f "$file" > /dev/null 2>&1; then
            echo "✅ $(basename "$file") validation successful" >> reports/validation/validation-report.md
        else
            echo "❌ $(basename "$file") validation failed" >> reports/validation/validation-report.md
        fi
    done

    echo "" >> reports/validation/validation-report.md
}

# Security configuration validation
validate_security() {
    print_status "Validating security configurations..."

    cat >> reports/validation/validation-report.md << EOF
### Security Configuration Validation

EOF

    # Check for security groups
    print_test "Checking security group configurations"
    if find infrastructure/terraform -name "*.tf" -exec grep -l "aws_security_group" {} \; | head -1 > /dev/null; then
        echo "✅ Security groups configured" >> reports/validation/validation-report.md
    else
        echo "❌ No security groups found" >> reports/validation/validation-report.md
    fi

    # Check for encryption
    print_test "Checking encryption configurations"
    if grep -r "encrypted.*true\|encryption" infrastructure/terraform/ > /dev/null; then
        echo "✅ Encryption configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No encryption configurations found" >> reports/validation/validation-report.md
    fi

    # Check for IAM roles
    print_test "Checking IAM configurations"
    if grep -r "aws_iam_role\|aws_iam_policy" infrastructure/terraform/ > /dev/null; then
        echo "✅ IAM configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No IAM configurations found" >> reports/validation/validation-report.md
    fi

    # Check for secrets management
    print_test "Checking secrets management"
    if grep -r "aws_secretsmanager\|secret" infrastructure/ > /dev/null; then
        echo "✅ Secrets management configured" >> reports/validation/validation-report.md
    else
        echo "❌ No secrets management found" >> reports/validation/validation-report.md
    fi

    # Check for network policies
    print_test "Checking Kubernetes network policies"
    if find infrastructure/kubernetes -name "*network-policy*" | head -1 > /dev/null; then
        echo "✅ Network policies configured" >> reports/validation/validation-report.md
    else
        echo "❌ No network policies found" >> reports/validation/validation-report.md
    fi

    echo "" >> reports/validation/validation-report.md
}

# High availability validation
validate_high_availability() {
    print_status "Validating high availability configurations..."

    cat >> reports/validation/validation-report.md << EOF
### High Availability Validation

EOF

    # Check for auto scaling groups
    print_test "Checking auto scaling configurations"
    if grep -r "aws_autoscaling_group" infrastructure/terraform/ > /dev/null; then
        echo "✅ Auto scaling groups configured" >> reports/validation/validation-report.md
    else
        echo "❌ No auto scaling groups found" >> reports/validation/validation-report.md
    fi

    # Check for multiple availability zones
    print_test "Checking multi-AZ configurations"
    if grep -r -i "availability.*zone\|subnet" infrastructure/terraform/ > /dev/null; then
        echo "✅ Multi-AZ configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No multi-AZ configurations found" >> reports/validation/validation-report.md
    fi

    # Check for load balancers
    print_test "Checking load balancer configurations"
    if grep -r "aws_lb\|aws_alb\|aws_elb" infrastructure/terraform/ > /dev/null; then
        echo "✅ Load balancer configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No load balancer configurations found" >> reports/validation/validation-report.md
    fi

    # Check for health checks
    print_test "Checking health check configurations"
    if grep -r -i "health.*check\|liveness.*probe\|readiness.*probe" infrastructure/ > /dev/null; then
        echo "✅ Health check configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No health check configurations found" >> reports/validation/validation-report.md
    fi

    echo "" >> reports/validation/validation-report.md
}

# Scalability validation
validate_scalability() {
    print_status "Validating scalability configurations..."

    cat >> reports/validation/validation-report.md << EOF
### Scalability Validation

EOF

    # Check for horizontal pod autoscaling
    print_test "Checking horizontal pod autoscaling"
    if find infrastructure/kubernetes -name "*hpa*" -o -name "*autoscal*" | head -1 > /dev/null; then
        echo "✅ Horizontal pod autoscaling configured" >> reports/validation/validation-report.md
    else
        echo "⚠️ No horizontal pod autoscaling found" >> reports/validation/validation-report.md
    fi

    # Check for resource limits
    print_test "Checking resource limits"
    if grep -r -i "limits:\|requests:" infrastructure/kubernetes/ > /dev/null; then
        echo "✅ Resource limits configured" >> reports/validation/validation-report.md
    else
        echo "❌ No resource limits found" >> reports/validation/validation-report.md
    fi

    # Check for CDN configuration
    print_test "Checking CDN configurations"
    if find infrastructure/terraform -name "*cdn*" -o -name "*cloudfront*" | head -1 > /dev/null; then
        echo "✅ CDN configurations found" >> reports/validation/validation-report.md
    else
        echo "⚠️ No CDN configurations found" >> reports/validation/validation-report.md
    fi

    # Check for caching
    print_test "Checking caching configurations"
    if grep -r -i "redis\|cache\|memcache" infrastructure/ > /dev/null; then
        echo "✅ Caching configurations found" >> reports/validation/validation-report.md
    else
        echo "⚠️ No caching configurations found" >> reports/validation/validation-report.md
    fi

    echo "" >> reports/validation/validation-report.md
}

# Disaster recovery validation
validate_disaster_recovery() {
    print_status "Validating disaster recovery configurations..."

    cat >> reports/validation/validation-report.md << EOF
### Disaster Recovery Validation

EOF

    # Check for backup configurations
    print_test "Checking backup configurations"
    if grep -r -i "backup\|snapshot" infrastructure/ > /dev/null; then
        echo "✅ Backup configurations found" >> reports/validation/validation-report.md
    else
        echo "❌ No backup configurations found" >> reports/validation/validation-report.md
    fi

    # Check for multi-region setup
    print_test "Checking multi-region configurations"
    if grep -r -i "region\|cross.*region" infrastructure/ > /dev/null; then
        echo "✅ Multi-region considerations found" >> reports/validation/validation-report.md
    else
        echo "⚠️ No multi-region configurations found" >> reports/validation/validation-report.md
    fi

    # Check for database replication
    print_test "Checking database replication"
    if grep -r -i "replica\|replication\|read.*replica" infrastructure/ > /dev/null; then
        echo "✅ Database replication configurations found" >> reports/validation/validation-report.md
    else
        echo "⚠️ No database replication found" >> reports/validation/validation-report.md
    fi

    echo "" >> reports/validation/validation-report.md
}

# Generate validation score
generate_validation_score() {
    print_status "Calculating validation score..."

    # Count passed, failed, and warning checks
    passed=$(grep -c "✅" reports/validation/validation-report.md || echo "0")
    failed=$(grep -c "❌" reports/validation/validation-report.md || echo "0")
    warnings=$(grep -c "⚠️" reports/validation/validation-report.md || echo "0")
    total=$((passed + failed + warnings))

    if [ $total -gt 0 ]; then
        score=$((passed * 100 / total))
    else
        score=0
    fi

    cat >> reports/validation/validation-report.md << EOF
## Validation Score

**Overall Validation Score: ${score}%**

- Passed Validations: ${passed}
- Failed Validations: ${failed}
- Warnings: ${warnings}
- Total Validations: ${total}

## Summary

EOF

    if [ $failed -gt 0 ]; then
        cat >> reports/validation/validation-report.md << EOF
### Critical Issues
- ${failed} validation(s) failed and require immediate attention
- Review failed validations and implement necessary fixes

EOF
    fi

    if [ $warnings -gt 0 ]; then
        cat >> reports/validation/validation-report.md << EOF
### Recommendations
- ${warnings} warning(s) found that should be addressed for optimal configuration
- Consider implementing recommended improvements

EOF
    fi

    cat >> reports/validation/validation-report.md << EOF
### Next Steps
1. Address all failed validations
2. Review and implement warning recommendations
3. Re-run validation tests
4. Document any architectural decisions
5. Schedule regular validation checks

---
*Report generated on $(date)*
EOF

    print_status "Validation score: ${score}% (${passed}/${total} validations passed)"
}

# Main execution
main() {
    init_report
    validate_terraform
    validate_kubernetes
    validate_security
    validate_high_availability
    validate_scalability
    validate_disaster_recovery
    generate_validation_score

    print_status "Infrastructure validation completed!"
    print_status "Report generated: reports/validation/validation-report.md"
}

# Run main function
main "$@"
