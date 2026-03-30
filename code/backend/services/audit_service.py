"""
Audit Service for BlockScore Backend
Comprehensive audit logging and monitoring for financial compliance
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from flask import request
from models.audit import AuditEventType, AuditLog, AuditSeverity


class AuditService:
    """Comprehensive audit service for financial compliance and security monitoring"""

    def __init__(self, db: Any) -> None:
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "ssn",
            "social_security",
            "credit_card",
            "bank_account",
            "routing_number",
            "pin",
        }
        self.risk_thresholds = {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
            "critical": 0.95,
        }

    def log_event(
        self,
        event_type: AuditEventType,
        event_description: str,
        user_id: str = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        resource_type: str = None,
        resource_id: str = None,
        event_data: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None,
        session_id: str = None,
        compliance_relevant: bool = False,
        risk_score: float = None,
    ) -> AuditLog:
        """Log a comprehensive audit event"""
        try:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=event_type,
                event_category=self._get_event_category(event_type),
                event_description=event_description,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                resource_type=resource_type,
                resource_id=resource_id,
                compliance_relevant=compliance_relevant,
                risk_score=risk_score
                or self._calculate_risk_score(event_type, event_data),
                event_timestamp=datetime.now(timezone.utc),
            )
            if event_data:
                sanitized_data = self._sanitize_sensitive_data(event_data)
                audit_log.set_event_data(sanitized_data)
            self.db.session.add(audit_log)
            self.db.session.commit()
            self._check_security_patterns(audit_log)
            return audit_log
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to create audit log: {e}")
            raise e

    def log_api_request(
        self,
        request_method: str,
        request_url: str,
        response_status: int,
        response_time_ms: int,
        ip_address: str = None,
        user_agent: str = None,
        user_id: str = None,
        request_body: Dict[str, Any] = None,
    ) -> AuditLog:
        """Log API request for monitoring and compliance"""
        try:
            event_type = self._determine_api_event_type(request_url, request_method)
            severity = self._determine_response_severity(response_status)
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=event_type,
                event_category="api_request",
                event_description=f"API Request: {request_method} {request_url}",
                severity=severity,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_method=request_method,
                request_url=request_url,
                response_status=response_status,
                response_time_ms=response_time_ms,
                compliance_relevant=self._is_compliance_relevant_endpoint(request_url),
                risk_score=self._calculate_api_risk_score(
                    request_method, request_url, response_status
                ),
                event_timestamp=datetime.now(timezone.utc),
            )
            if hasattr(request, "headers"):
                audit_log.set_request_headers(dict(request.headers))
            if request_body:
                sanitized_body = self._sanitize_sensitive_data(request_body)
                audit_log.request_body = json.dumps(sanitized_body)
            self.db.session.add(audit_log)
            self.db.session.commit()
            return audit_log
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to log API request: {e}")
            return None

    def log_data_change(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        before_state: Dict[str, Any] = None,
        after_state: Dict[str, Any] = None,
        change_reason: str = None,
    ) -> AuditLog:
        """Log data changes for audit trail"""
        try:
            event_type = AuditEventType.DATA_ACCESS
            if action in ["create", "insert"]:
                event_description = f"Created {resource_type}: {resource_id}"
            elif action in ["update", "modify"]:
                event_description = f"Updated {resource_type}: {resource_id}"
            elif action in ["delete", "remove"]:
                event_description = f"Deleted {resource_type}: {resource_id}"
                event_type = AuditEventType.ADMIN_ACTION
            else:
                event_description = f"Changed {resource_type}: {resource_id} ({action})"
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=event_type,
                event_category="data_change",
                event_description=event_description,
                severity=(
                    AuditSeverity.MEDIUM if action == "delete" else AuditSeverity.LOW
                ),
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                compliance_relevant=True,
                event_timestamp=datetime.now(timezone.utc),
            )
            if before_state:
                sanitized_before = self._sanitize_sensitive_data(before_state)
                audit_log.set_before_state(sanitized_before)
            if after_state:
                sanitized_after = self._sanitize_sensitive_data(after_state)
                audit_log.set_after_state(sanitized_after)
            event_data = {
                "action": action,
                "change_reason": change_reason,
                "changed_fields": self._get_changed_fields(before_state, after_state),
            }
            audit_log.set_event_data(event_data)
            self.db.session.add(audit_log)
            self.db.session.commit()
            return audit_log
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to log data change: {e}")
            raise e

    def log_security_event(
        self,
        event_type: str,
        description: str,
        user_id: str = None,
        ip_address: str = None,
        severity: AuditSeverity = AuditSeverity.HIGH,
        event_data: Dict[str, Any] = None,
    ) -> AuditLog:
        """Log security-related events"""
        return self.log_event(
            event_type=AuditEventType.SECURITY_ALERT,
            event_description=f"Security Event: {event_type} - {description}",
            user_id=user_id,
            severity=severity,
            ip_address=ip_address,
            event_data=event_data or {"security_event_type": event_type},
            compliance_relevant=True,
            risk_score=0.8,
        )

    def log_compliance_event(
        self,
        compliance_type: str,
        description: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        event_data: Dict[str, Any] = None,
    ) -> AuditLog:
        """Log compliance-related events"""
        return self.log_event(
            event_type=AuditEventType.COMPLIANCE_CHECK,
            event_description=f"Compliance Event: {compliance_type} - {description}",
            user_id=user_id,
            severity=AuditSeverity.MEDIUM,
            resource_type=resource_type,
            resource_id=resource_id,
            event_data=event_data or {"compliance_type": compliance_type},
            compliance_relevant=True,
        )

    def get_audit_trail(
        self,
        resource_type: str = None,
        resource_id: str = None,
        user_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit trail with filtering options"""
        query = AuditLog.query
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.event_timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.event_timestamp <= end_date)
        audit_logs = query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
        return [log.to_dict() for log in audit_logs]

    def get_security_alerts(
        self,
        severity: AuditSeverity = None,
        start_date: datetime = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get security alerts"""
        query = AuditLog.query.filter(
            AuditLog.event_type == AuditEventType.SECURITY_ALERT
        )
        if severity:
            query = query.filter(AuditLog.severity == severity)
        if start_date:
            query = query.filter(AuditLog.event_timestamp >= start_date)
        alerts = query.order_by(AuditLog.event_timestamp.desc()).limit(limit).all()
        return [alert.to_dict() for alert in alerts]

    def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        compliance_types: List[str] = None,
    ) -> Dict[str, Any]:
        """Generate compliance report"""
        query = AuditLog.query.filter(
            AuditLog.compliance_relevant,
            AuditLog.event_timestamp >= start_date,
            AuditLog.event_timestamp <= end_date,
        )
        if compliance_types:
            query = query.filter(
                AuditLog.event_type.in_(
                    [AuditEventType.COMPLIANCE_CHECK]
                    + [
                        getattr(
                            AuditEventType, ct.upper(), AuditEventType.COMPLIANCE_CHECK
                        )
                        for ct in compliance_types
                        if hasattr(AuditEventType, ct.upper())
                    ]
                )
            )
        logs = query.all()
        total_events = len(logs)
        events_by_type = {}
        events_by_severity = {}
        events_by_user = {}
        for log in logs:
            event_type = log.event_type.value
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
            severity = log.severity.value
            events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
            if log.user_id:
                events_by_user[log.user_id] = events_by_user.get(log.user_id, 0) + 1
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "summary": {
                "total_events": total_events,
                "compliance_events": total_events,
                "security_alerts": len(
                    [l for l in logs if l.event_type == AuditEventType.SECURITY_ALERT]
                ),
                "high_risk_events": len(
                    [l for l in logs if l.risk_score and l.risk_score > 0.7]
                ),
            },
            "breakdown": {
                "by_event_type": events_by_type,
                "by_severity": events_by_severity,
                "by_user": dict(list(events_by_user.items())[:10]),
            },
            "recent_events": [log.to_dict() for log in logs[:20]],
        }

    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        logs = (
            AuditLog.query.filter(
                AuditLog.user_id == user_id, AuditLog.event_timestamp >= start_date
            )
            .order_by(AuditLog.event_timestamp.desc())
            .all()
        )
        total_activities = len(logs)
        login_events = len(
            [l for l in logs if l.event_type == AuditEventType.USER_LOGIN]
        )
        api_requests = len([l for l in logs if l.event_category == "api_request"])
        security_events = len(
            [l for l in logs if l.event_type == AuditEventType.SECURITY_ALERT]
        )
        unique_ips = set((log.ip_address for log in logs if log.ip_address))
        activity_by_day = {}
        for log in logs:
            day = log.event_timestamp.date().isoformat()
            activity_by_day[day] = activity_by_day.get(day, 0) + 1
        return {
            "user_id": user_id,
            "period_days": days,
            "summary": {
                "total_activities": total_activities,
                "login_events": login_events,
                "api_requests": api_requests,
                "security_events": security_events,
                "unique_ip_addresses": len(unique_ips),
            },
            "activity_by_day": activity_by_day,
            "recent_activities": [log.to_dict() for log in logs[:10]],
        }

    def _get_event_category(self, event_type: AuditEventType) -> str:
        """Get event category for audit event type"""
        category_mapping = {
            AuditEventType.USER_LOGIN: "authentication",
            AuditEventType.USER_LOGOUT: "authentication",
            AuditEventType.USER_REGISTRATION: "authentication",
            AuditEventType.PASSWORD_CHANGE: "authentication",
            AuditEventType.PROFILE_UPDATE: "user_management",
            AuditEventType.CREDIT_SCORE_CALCULATION: "credit_scoring",
            AuditEventType.LOAN_APPLICATION: "lending",
            AuditEventType.LOAN_APPROVAL: "lending",
            AuditEventType.LOAN_DISBURSEMENT: "lending",
            AuditEventType.PAYMENT_PROCESSED: "payments",
            AuditEventType.DATA_ACCESS: "data_access",
            AuditEventType.DATA_EXPORT: "data_access",
            AuditEventType.ADMIN_ACTION: "administration",
            AuditEventType.SECURITY_ALERT: "security",
            AuditEventType.COMPLIANCE_CHECK: "compliance",
            AuditEventType.BLOCKCHAIN_TRANSACTION: "blockchain",
        }
        return category_mapping.get(event_type, "general")

    def _calculate_risk_score(
        self, event_type: AuditEventType, event_data: Dict[str, Any] = None
    ) -> float:
        """Calculate risk score for event"""
        base_risk_scores = {
            AuditEventType.USER_LOGIN: 0.1,
            AuditEventType.USER_LOGOUT: 0.05,
            AuditEventType.USER_REGISTRATION: 0.3,
            AuditEventType.PASSWORD_CHANGE: 0.4,
            AuditEventType.PROFILE_UPDATE: 0.2,
            AuditEventType.CREDIT_SCORE_CALCULATION: 0.2,
            AuditEventType.LOAN_APPLICATION: 0.5,
            AuditEventType.LOAN_APPROVAL: 0.6,
            AuditEventType.LOAN_DISBURSEMENT: 0.7,
            AuditEventType.PAYMENT_PROCESSED: 0.3,
            AuditEventType.DATA_ACCESS: 0.3,
            AuditEventType.DATA_EXPORT: 0.6,
            AuditEventType.ADMIN_ACTION: 0.8,
            AuditEventType.SECURITY_ALERT: 0.9,
            AuditEventType.COMPLIANCE_CHECK: 0.4,
            AuditEventType.BLOCKCHAIN_TRANSACTION: 0.3,
        }
        base_score = base_risk_scores.get(event_type, 0.2)
        if event_data:
            if event_data.get("failed_attempt"):
                base_score += 0.2
            if event_data.get("suspicious_activity"):
                base_score += 0.3
            if event_data.get("high_value_transaction"):
                base_score += 0.2
        return min(1.0, base_score)

    def _determine_api_event_type(self, url: str, method: str) -> AuditEventType:
        """Determine audit event type based on API endpoint"""
        if "/auth/" in url:
            if "login" in url:
                return AuditEventType.USER_LOGIN
            elif "register" in url:
                return AuditEventType.USER_REGISTRATION
            elif "logout" in url:
                return AuditEventType.USER_LOGOUT
        elif "/credit/" in url:
            return AuditEventType.CREDIT_SCORE_CALCULATION
        elif "/loans/" in url:
            if method == "POST":
                return AuditEventType.LOAN_APPLICATION
            else:
                return AuditEventType.DATA_ACCESS
        elif "/profile" in url:
            if method in ["PUT", "PATCH"]:
                return AuditEventType.PROFILE_UPDATE
            else:
                return AuditEventType.DATA_ACCESS
        return AuditEventType.DATA_ACCESS

    def _determine_response_severity(self, status_code: int) -> AuditSeverity:
        """Determine severity based on HTTP response status"""
        if status_code >= 500:
            return AuditSeverity.HIGH
        elif status_code >= 400:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW

    def _calculate_api_risk_score(
        self, method: str, url: str, status_code: int
    ) -> float:
        """Calculate risk score for API request"""
        base_score = 0.1
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            base_score += 0.2
        if any(
            (
                endpoint in url
                for endpoint in ["/auth/", "/admin/", "/loans/", "/credit/"]
            )
        ):
            base_score += 0.2
        if status_code >= 400:
            base_score += 0.3
        return min(1.0, base_score)

    def _is_compliance_relevant_endpoint(self, url: str) -> bool:
        """Check if endpoint is compliance relevant"""
        compliance_endpoints = [
            "/auth/",
            "/profile",
            "/credit/",
            "/loans/",
            "/payments/",
            "/admin/",
            "/compliance/",
            "/audit/",
        ]
        return any((endpoint in url for endpoint in compliance_endpoints))

    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive data from audit logs"""
        if not isinstance(data, dict):
            return data
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any((sensitive in key_lower for sensitive in self.sensitive_fields)):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_sensitive_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    (
                        self._sanitize_sensitive_data(item)
                        if isinstance(item, dict)
                        else item
                    )
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def _get_changed_fields(
        self, before_state: Dict[str, Any] = None, after_state: Dict[str, Any] = None
    ) -> List[str]:
        """Get list of fields that changed between states"""
        if not before_state or not after_state:
            return []
        changed_fields = []
        all_keys = set(before_state.keys()) | set(after_state.keys())
        for key in all_keys:
            before_value = before_state.get(key)
            after_value = after_state.get(key)
            if before_value != after_value:
                changed_fields.append(key)
        return changed_fields

    def _check_security_patterns(self, audit_log: AuditLog) -> Any:
        """Check for suspicious patterns in audit logs"""
        try:
            if (
                audit_log.event_type == AuditEventType.USER_LOGIN
                and audit_log.severity == AuditSeverity.MEDIUM
            ):
                self._check_failed_login_pattern(audit_log)
            if audit_log.event_category == "api_request":
                self._check_api_access_pattern(audit_log)
            if audit_log.risk_score and audit_log.risk_score > 0.8:
                self._create_security_alert(audit_log, "High risk event detected")
        except Exception as e:
            self.logger.error(f"Failed to check security patterns: {e}")

    def _check_failed_login_pattern(self, audit_log: AuditLog) -> Any:
        """Check for suspicious failed login patterns"""
        if not audit_log.ip_address:
            return
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        failed_attempts = AuditLog.query.filter(
            AuditLog.event_type == AuditEventType.USER_LOGIN,
            AuditLog.severity == AuditSeverity.MEDIUM,
            AuditLog.ip_address == audit_log.ip_address,
            AuditLog.event_timestamp >= cutoff_time,
        ).count()
        if failed_attempts >= 5:
            self._create_security_alert(
                audit_log,
                f"Multiple failed login attempts from IP: {audit_log.ip_address}",
            )

    def _check_api_access_pattern(self, audit_log: AuditLog) -> Any:
        """Check for unusual API access patterns"""
        if not audit_log.ip_address:
            return
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_requests = AuditLog.query.filter(
            AuditLog.event_category == "api_request",
            AuditLog.ip_address == audit_log.ip_address,
            AuditLog.event_timestamp >= cutoff_time,
        ).count()
        if recent_requests >= 100:
            self._create_security_alert(
                audit_log,
                f"High frequency API requests from IP: {audit_log.ip_address}",
            )

    def _create_security_alert(self, related_log: AuditLog, alert_message: str) -> Any:
        """Create a security alert based on detected patterns"""
        try:
            alert = AuditLog(
                id=str(uuid.uuid4()),
                event_type=AuditEventType.SECURITY_ALERT,
                event_category="security",
                event_description=f"Security Alert: {alert_message}",
                severity=AuditSeverity.HIGH,
                user_id=related_log.user_id,
                ip_address=related_log.ip_address,
                user_agent=related_log.user_agent,
                compliance_relevant=True,
                risk_score=0.9,
                event_timestamp=datetime.now(timezone.utc),
            )
            alert.set_event_data(
                {
                    "alert_type": "pattern_detection",
                    "related_log_id": related_log.id,
                    "alert_message": alert_message,
                }
            )
            self.db.session.add(alert)
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to create security alert: {e}")
