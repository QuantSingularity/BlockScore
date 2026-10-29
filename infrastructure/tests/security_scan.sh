#!/bin/bash

# BlockScore Infrastructure Security Scan Script
# This script performs comprehensive security scans on the infrastructure code

set -e

echo "Starting BlockScore Infrastructure Security Scan..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if required tools are installed
check_dependencies() {
    print_status "Checking dependencies..."

    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed"
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed - some scans may be skipped"
    fi

    print_status "Dependencies check completed"
}

# Terraform security scan using Checkov
terraform_security_scan() {
    print_status "Running Terraform security scan with Checkov..."

    if command -v checkov &> /dev/null; then
        checkov -d infrastructure/terraform/ --framework terraform --output cli --output json --output-file-path reports/terraform-security-scan.json
    else
        print_warning "Checkov not installed, running with Docker..."
        docker run --rm -v $(pwd):/tf bridgecrew/checkov -d /tf/infrastructure/terraform/ --framework terraform --output cli --output json --output-file-path /tf/reports/terraform-security-scan.json
    fi

    print_status "Terraform security scan completed"
}

# Terraform format and validation
terraform_validation() {
    print_status "Running Terraform validation..."

    cd infrastructure/terraform

    # Format check
    if ! terraform fmt -check -recursive .; then
        print_error "Terraform formatting issues found"
        terraform fmt -recursive .
        print_status "Terraform files formatted"
    fi

    # Initialize and validate
    terraform init -backend=false
    terraform validate

    cd ../..
    print_status "Terraform validation completed"
}

# Kubernetes security scan
kubernetes_security_scan() {
    print_status "Running Kubernetes security scan..."

    # Validate Kubernetes manifests
    find infrastructure/kubernetes -name "*.yaml" -o -name "*.yml" | while read -r file; do
        print_status "Validating $file"
        kubectl apply --dry-run=client --validate=true -f "$file"
    done

    # Run Kubesec scan if available
    if command -v kubesec &> /dev/null; then
        find infrastructure/kubernetes -name "*.yaml" -o -name "*.yml" | while read -r file; do
            print_status "Running Kubesec scan on $file"
            kubesec scan "$file" > "reports/kubesec-$(basename "$file").json"
        done
    else
        print_warning "Kubesec not installed, running with curl..."
        find infrastructure/kubernetes -name "*.yaml" -o -name "*.yml" | while read -r file; do
            print_status "Running Kubesec scan on $file"
            curl -sSX POST --data-binary @"$file" https://v2.kubesec.io/scan > "reports/kubesec-$(basename "$file").json"
        done
    fi

    print_status "Kubernetes security scan completed"
}

# Ansible security scan
ansible_security_scan() {
    print_status "Running Ansible security scan..."

    if command -v ansible-lint &> /dev/null; then
        ansible-lint infrastructure/ansible/ > reports/ansible-lint-report.txt || true
    else
        print_warning "ansible-lint not installed, skipping Ansible security scan"
    fi

    print_status "Ansible security scan completed"
}

# Check for secrets in code
secrets_scan() {
    print_status "Scanning for secrets in code..."

    if command -v truffleHog &> /dev/null; then
        truffleHog --regex --entropy=False infrastructure/ > reports/secrets-scan.txt || true
    elif command -v git-secrets &> /dev/null; then
        git secrets --scan infrastructure/ > reports/secrets-scan.txt || true
    else
        print_warning "No secrets scanning tool found (truffleHog or git-secrets)"
        # Basic grep for common secret patterns
        grep -r -i -E "(password|secret|key|token|api_key)" infrastructure/ --exclude-dir=.git > reports/basic-secrets-scan.txt || true
    fi

    print_status "Secrets scan completed"
}

# Network security validation
network_security_validation() {
    print_status "Validating network security configurations..."

    # Check for proper security group configurations
    grep -r "0.0.0.0/0" infrastructure/terraform/ > reports/open-security-groups.txt || true

    # Check for unencrypted resources
    grep -r -i "encrypt" infrastructure/terraform/ > reports/encryption-check.txt || true

    print_status "Network security validation completed"
}

# Compliance checks
compliance_checks() {
    print_status "Running compliance checks..."

    # Check for required tags
    grep -r -i "environment" infrastructure/terraform/ > reports/tagging-compliance.txt || true

    # Check for logging configurations
    grep -r -i "log" infrastructure/ > reports/logging-compliance.txt || true

    # Check for backup configurations
    grep -r -i "backup" infrastructure/ > reports/backup-compliance.txt || true

    print_status "Compliance checks completed"
}

# Generate summary report
generate_summary() {
    print_status "Generating summary report..."

    cat > reports/security-scan-summary.md << EOF
# BlockScore Infrastructure Security Scan Summary

## Scan Date
$(date)

## Scans Performed
- Terraform Security Scan (Checkov)
- Terraform Validation
- Kubernetes Security Scan (Kubesec)
- Ansible Security Scan (ansible-lint)
- Secrets Scan
- Network Security Validation
- Compliance Checks

## Report Files Generated
- terraform-security-scan.json
- kubesec-*.json
- ansible-lint-report.txt
- secrets-scan.txt
- open-security-groups.txt
- encryption-check.txt
- tagging-compliance.txt
- logging-compliance.txt
- backup-compliance.txt

## Recommendations
1. Review all security scan results
2. Address any high-severity findings
3. Ensure all secrets are properly managed
4. Verify encryption is enabled for all sensitive data
5. Confirm compliance with financial industry standards

## Next Steps
1. Fix identified security issues
2. Re-run security scans
3. Update documentation
4. Schedule regular security scans
EOF

    print_status "Summary report generated: reports/security-scan-summary.md"
}

# Main execution
main() {
    # Create reports directory
    mkdir -p reports

    check_dependencies
    terraform_validation
    terraform_security_scan
    kubernetes_security_scan
    ansible_security_scan
    secrets_scan
    network_security_validation
    compliance_checks
    generate_summary

    print_status "Security scan completed successfully!"
    print_status "Review the reports in the 'reports' directory"
}

# Run main function
main "$@"
