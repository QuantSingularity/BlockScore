#!/bin/bash

# BlockScore Infrastructure Compliance Check Script
# This script validates compliance with financial industry standards

set -e

echo "Starting BlockScore Infrastructure Compliance Check..."

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

print_check() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# Initialize compliance report
init_report() {
    mkdir -p reports/compliance
    cat > reports/compliance/compliance-report.md << EOF
# BlockScore Infrastructure Compliance Report

## Report Date
$(date)

## Compliance Standards Checked
- PCI DSS (Payment Card Industry Data Security Standard)
- SOX (Sarbanes-Oxley Act)
- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- Financial Industry Best Practices

## Compliance Checks

EOF
}

# PCI DSS Compliance Checks
check_pci_dss() {
    print_status "Checking PCI DSS compliance..."

    cat >> reports/compliance/compliance-report.md << EOF
### PCI DSS Compliance

EOF

    # Requirement 1: Install and maintain a firewall configuration
    print_check "PCI DSS Req 1: Firewall configuration"
    if grep -r "aws_security_group" infrastructure/terraform/ > /dev/null; then
        echo "✅ Security groups configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ No security groups found" >> reports/compliance/compliance-report.md
    fi

    # Requirement 2: Do not use vendor-supplied defaults for system passwords
    print_check "PCI DSS Req 2: Default passwords"
    if grep -r -i "default.*password\|admin.*admin\|password.*password" infrastructure/ > /dev/null; then
        echo "❌ Default passwords found" >> reports/compliance/compliance-report.md
    else
        echo "✅ No default passwords detected" >> reports/compliance/compliance-report.md
    fi

    # Requirement 3: Protect stored cardholder data
    print_check "PCI DSS Req 3: Data encryption"
    if grep -r "storage_encrypted.*true\|encrypted.*true" infrastructure/terraform/ > /dev/null; then
        echo "✅ Storage encryption enabled" >> reports/compliance/compliance-report.md
    else
        echo "❌ Storage encryption not found" >> reports/compliance/compliance-report.md
    fi

    # Requirement 4: Encrypt transmission of cardholder data
    print_check "PCI DSS Req 4: Data transmission encryption"
    if grep -r -i "tls\|ssl\|https" infrastructure/ > /dev/null; then
        echo "✅ Encryption in transit configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Encryption in transit not found" >> reports/compliance/compliance-report.md
    fi

    # Requirement 6: Develop and maintain secure systems
    print_check "PCI DSS Req 6: Secure systems"
    if [ -f "infrastructure/ci-cd/github-actions/terraform-ci.yml" ]; then
        echo "✅ CI/CD pipeline with security checks" >> reports/compliance/compliance-report.md
    else
        echo "❌ No CI/CD security pipeline found" >> reports/compliance/compliance-report.md
    fi

    # Requirement 10: Track and monitor all access to network resources
    print_check "PCI DSS Req 10: Access monitoring"
    if grep -r -i "cloudtrail\|audit.*log\|access.*log" infrastructure/ > /dev/null; then
        echo "✅ Access monitoring configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Access monitoring not found" >> reports/compliance/compliance-report.md
    fi

    echo "" >> reports/compliance/compliance-report.md
}

# SOX Compliance Checks
check_sox() {
    print_status "Checking SOX compliance..."

    cat >> reports/compliance/compliance-report.md << EOF
### SOX Compliance

EOF

    # Section 302: Corporate responsibility for financial reports
    print_check "SOX Sec 302: Financial reporting controls"
    if grep -r -i "audit\|log\|trail" infrastructure/ > /dev/null; then
        echo "✅ Audit trails configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Audit trails not found" >> reports/compliance/compliance-report.md
    fi

    # Section 404: Management assessment of internal controls
    print_check "SOX Sec 404: Internal controls"
    if [ -f "infrastructure/terraform/modules/security/main.tf" ]; then
        echo "✅ Security controls implemented" >> reports/compliance/compliance-report.md
    else
        echo "❌ Security controls not found" >> reports/compliance/compliance-report.md
    fi

    # Data retention requirements
    print_check "SOX: Data retention"
    if grep -r "retention" infrastructure/ > /dev/null; then
        echo "✅ Data retention policies configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Data retention policies not found" >> reports/compliance/compliance-report.md
    fi

    echo "" >> reports/compliance/compliance-report.md
}

# GDPR Compliance Checks
check_gdpr() {
    print_status "Checking GDPR compliance..."

    cat >> reports/compliance/compliance-report.md << EOF
### GDPR Compliance

EOF

    # Article 25: Data protection by design and by default
    print_check "GDPR Art 25: Data protection by design"
    if grep -r "encrypt" infrastructure/ > /dev/null; then
        echo "✅ Encryption configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Encryption not found" >> reports/compliance/compliance-report.md
    fi

    # Article 30: Records of processing activities
    print_check "GDPR Art 30: Processing records"
    if grep -r -i "log\|audit" infrastructure/ > /dev/null; then
        echo "✅ Processing logs configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Processing logs not found" >> reports/compliance/compliance-report.md
    fi

    # Article 32: Security of processing
    print_check "GDPR Art 32: Security measures"
    if grep -r -i "security.*group\|firewall\|waf" infrastructure/ > /dev/null; then
        echo "✅ Security measures implemented" >> reports/compliance/compliance-report.md
    else
        echo "❌ Security measures not found" >> reports/compliance/compliance-report.md
    fi

    echo "" >> reports/compliance/compliance-report.md
}

# CCPA Compliance Checks
check_ccpa() {
    print_status "Checking CCPA compliance..."

    cat >> reports/compliance/compliance-report.md << EOF
### CCPA Compliance

EOF

    # Data security requirements
    print_check "CCPA: Data security"
    if grep -r "encrypt" infrastructure/ > /dev/null; then
        echo "✅ Data security measures configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Data security measures not found" >> reports/compliance/compliance-report.md
    fi

    # Access controls
    print_check "CCPA: Access controls"
    if grep -r -i "iam\|rbac\|access.*control" infrastructure/ > /dev/null; then
        echo "✅ Access controls configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Access controls not found" >> reports/compliance/compliance-report.md
    fi

    echo "" >> reports/compliance/compliance-report.md
}

# Financial Industry Best Practices
check_financial_best_practices() {
    print_status "Checking financial industry best practices..."

    cat >> reports/compliance/compliance-report.md << EOF
### Financial Industry Best Practices

EOF

    # Multi-factor authentication
    print_check "Best Practice: Multi-factor authentication"
    if grep -r -i "mfa\|multi.*factor" infrastructure/ > /dev/null; then
        echo "✅ MFA configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ MFA not found" >> reports/compliance/compliance-report.md
    fi

    # Network segmentation
    print_check "Best Practice: Network segmentation"
    if grep -r -i "subnet\|vpc\|network" infrastructure/terraform/ > /dev/null; then
        echo "✅ Network segmentation configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Network segmentation not found" >> reports/compliance/compliance-report.md
    fi

    # Backup and disaster recovery
    print_check "Best Practice: Backup and DR"
    if grep -r -i "backup\|disaster.*recovery\|multi.*region" infrastructure/ > /dev/null; then
        echo "✅ Backup and DR considerations found" >> reports/compliance/compliance-report.md
    else
        echo "❌ Backup and DR not found" >> reports/compliance/compliance-report.md
    fi

    # Monitoring and alerting
    print_check "Best Practice: Monitoring and alerting"
    if grep -r -i "cloudwatch\|monitor\|alert" infrastructure/ > /dev/null; then
        echo "✅ Monitoring and alerting configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Monitoring and alerting not found" >> reports/compliance/compliance-report.md
    fi

    # Secrets management
    print_check "Best Practice: Secrets management"
    if grep -r -i "secret.*manager\|vault\|kms" infrastructure/ > /dev/null; then
        echo "✅ Secrets management configured" >> reports/compliance/compliance-report.md
    else
        echo "❌ Secrets management not found" >> reports/compliance/compliance-report.md
    fi

    echo "" >> reports/compliance/compliance-report.md
}

# Generate compliance score
generate_compliance_score() {
    print_status "Calculating compliance score..."

    # Count passed and failed checks
    passed=$(grep -c "✅" reports/compliance/compliance-report.md || echo "0")
    failed=$(grep -c "❌" reports/compliance/compliance-report.md || echo "0")
    total=$((passed + failed))

    if [ $total -gt 0 ]; then
        score=$((passed * 100 / total))
    else
        score=0
    fi

    cat >> reports/compliance/compliance-report.md << EOF
## Compliance Score

**Overall Compliance Score: ${score}%**

- Passed Checks: ${passed}
- Failed Checks: ${failed}
- Total Checks: ${total}

## Recommendations

EOF

    if [ $failed -gt 0 ]; then
        cat >> reports/compliance/compliance-report.md << EOF
### Critical Actions Required
1. Address all failed compliance checks immediately
2. Implement missing security controls
3. Review and update policies and procedures
4. Schedule regular compliance audits

EOF
    fi

    cat >> reports/compliance/compliance-report.md << EOF
### General Recommendations
1. Implement continuous compliance monitoring
2. Regular security assessments and penetration testing
3. Staff training on compliance requirements
4. Document all security and compliance procedures
5. Establish incident response procedures

## Next Steps
1. Review all failed checks in detail
2. Create remediation plan with timelines
3. Implement required changes
4. Re-run compliance checks
5. Schedule regular compliance reviews

---
*Report generated on $(date)*
EOF

    print_status "Compliance score: ${score}% (${passed}/${total} checks passed)"
}

# Main execution
main() {
    init_report
    check_pci_dss
    check_sox
    check_gdpr
    check_ccpa
    check_financial_best_practices
    generate_compliance_score

    print_status "Compliance check completed!"
    print_status "Report generated: reports/compliance/compliance-report.md"
}

# Run main function
main "$@"
