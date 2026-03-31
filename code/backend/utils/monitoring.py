"""
Performance Monitoring for BlockScore Backend
Real-time performance monitoring and alerting
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List

import psutil


@dataclass
class MetricPoint:
    """Single metric data point"""

    timestamp: datetime
    value: float
    tags: Dict[str, str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags or {},
        }


class PerformanceMonitor:
    """Real-time performance monitoring system"""

    def __init__(self, retention_hours: int = 24) -> None:
        self.retention_hours = retention_hours
        self.metrics = defaultdict(lambda: deque(maxlen=10000))
        self.alerts = []
        self.alert_rules = {}
        self.logger = logging.getLogger(__name__)
        self.request_counts = defaultdict(int)
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.system_metrics_enabled = True
        self._start_system_monitoring()
        self.default_thresholds = {
            "response_time_ms": 1000,
            "error_rate_percent": 5.0,
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
        }

    def record_metric(
        self, name: str, value: float, tags: Dict[str, str] = None
    ) -> Any:
        """Record a metric value"""
        try:
            point = MetricPoint(
                timestamp=datetime.now(timezone.utc), value=value, tags=tags
            )
            self.metrics[name].append(point)
            self._check_alerts(name, value, tags)
            self._cleanup_old_metrics(name)
        except Exception as e:
            self.logger.error(f"Failed to record metric {name}: {e}")

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        user_id: str = None,
    ) -> Any:
        """Record HTTP request metrics"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code),
            "status_class": f"{status_code // 100}xx",
        }
        if user_id:
            tags["user_id"] = user_id
        self.record_metric("http_requests_total", 1, tags)
        self.record_metric("http_request_duration_ms", response_time_ms, tags)
        key = f"{method}:{endpoint}"
        self.request_counts[key] += 1
        self.response_times[key].append(response_time_ms)
        if status_code >= 400:
            self.error_counts[key] += 1
            self.record_metric("http_errors_total", 1, tags)

    def record_database_query(
        self,
        query_type: str,
        table: str,
        execution_time_ms: float,
        rows_affected: int = 0,
    ) -> Any:
        """Record database query metrics"""
        tags = {"query_type": query_type, "table": table}
        self.record_metric("db_query_duration_ms", execution_time_ms, tags)
        self.record_metric("db_query_total", 1, tags)
        if rows_affected > 0:
            self.record_metric("db_rows_affected", rows_affected, tags)

    def record_cache_operation(
        self, operation: str, hit: bool, execution_time_ms: float = None
    ) -> Any:
        """Record cache operation metrics"""
        tags = {"operation": operation, "result": "hit" if hit else "miss"}
        self.record_metric("cache_operations_total", 1, tags)
        if execution_time_ms is not None:
            self.record_metric("cache_operation_duration_ms", execution_time_ms, tags)

    def record_business_metric(
        self, metric_name: str, value: float, tags: Dict[str, str] = None
    ) -> Any:
        """Record business-specific metrics"""
        business_tags = {"category": "business"}
        if tags:
            business_tags.update(tags)
        self.record_metric(f"business_{metric_name}", value, business_tags)

    def get_metrics(
        self,
        name: str,
        start_time: datetime = None,
        end_time: datetime = None,
        tags: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        """Get metric values within time range"""
        try:
            if name not in self.metrics:
                return []
            points = list(self.metrics[name])
            if start_time or end_time:
                filtered_points = []
                for point in points:
                    if start_time and point.timestamp < start_time:
                        continue
                    if end_time and point.timestamp > end_time:
                        continue
                    filtered_points.append(point)
                points = filtered_points
            if tags:
                filtered_points = []
                for point in points:
                    if point.tags and all(
                        (point.tags.get(k) == v for k, v in tags.items())
                    ):
                        filtered_points.append(point)
                points = filtered_points
            return [point.to_dict() for point in points]
        except Exception as e:
            self.logger.error(f"Failed to get metrics for {name}: {e}")
            return []

    def get_metric_summary(
        self, name: str, start_time: datetime = None, end_time: datetime = None
    ) -> Dict[str, Any]:
        """Get metric summary statistics"""
        try:
            points = self.get_metrics(name, start_time, end_time)
            if not points:
                return {"count": 0}
            values = [p["value"] for p in points]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "sum": sum(values),
                "first_timestamp": points[0]["timestamp"],
                "last_timestamp": points[-1]["timestamp"],
            }
        except Exception as e:
            self.logger.error(f"Failed to get metric summary for {name}: {e}")
            return {"error": str(e)}

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            try:
                network = psutil.net_io_counters()
                network_metrics = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                }
            except Exception:
                network_metrics = {}
            return {
                "cpu": {"percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                },
                "network": network_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}

    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            response_time_stats = {}
            for endpoint, times in self.response_times.items():
                if times:
                    sorted_times = sorted(times)
                    count = len(sorted_times)
                    response_time_stats[endpoint] = {
                        "count": count,
                        "avg": sum(sorted_times) / count,
                        "p50": sorted_times[int(count * 0.5)],
                        "p95": sorted_times[int(count * 0.95)],
                        "p99": (
                            sorted_times[int(count * 0.99)]
                            if count > 10
                            else sorted_times[-1]
                        ),
                    }
            error_rates = {}
            for endpoint in self.request_counts:
                total_requests = self.request_counts[endpoint]
                error_count = self.error_counts.get(endpoint, 0)
                error_rates[endpoint] = {
                    "total_requests": total_requests,
                    "error_count": error_count,
                    "error_rate": (
                        error_count / total_requests * 100 if total_requests > 0 else 0
                    ),
                }
            return {
                "response_times": response_time_stats,
                "error_rates": error_rates,
                "total_requests": sum(self.request_counts.values()),
                "total_errors": sum(self.error_counts.values()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get application metrics: {e}")
            return {"error": str(e)}

    def add_alert_rule(
        self,
        name: str,
        metric_name: str,
        threshold: float,
        operator: str = "gt",
        tags: Dict[str, str] = None,
        callback: Callable = None,
    ) -> Any:
        """Add alert rule for metric"""
        self.alert_rules[name] = {
            "metric_name": metric_name,
            "threshold": threshold,
            "operator": operator,
            "tags": tags or {},
            "callback": callback,
            "created_at": datetime.now(timezone.utc),
        }
        self.logger.info(f"Alert rule added: {name}")

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
        active_alerts = [
            alert for alert in self.alerts if alert["timestamp"] > cutoff_time
        ]
        return active_alerts

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            system_metrics = self.get_system_metrics()
            app_metrics = self.get_application_metrics()
            active_alerts = self.get_active_alerts()
            health_score = 100
            issues = []
            if "error" not in system_metrics:
                if (
                    system_metrics["cpu"]["percent"]
                    > self.default_thresholds["cpu_percent"]
                ):
                    health_score -= 20
                    issues.append(
                        f"High CPU usage: {system_metrics['cpu']['percent']:.1f}%"
                    )
                if (
                    system_metrics["memory"]["percent"]
                    > self.default_thresholds["memory_percent"]
                ):
                    health_score -= 20
                    issues.append(
                        f"High memory usage: {system_metrics['memory']['percent']:.1f}%"
                    )
                if (
                    system_metrics["disk"]["percent"]
                    > self.default_thresholds["disk_percent"]
                ):
                    health_score -= 15
                    issues.append(
                        f"High disk usage: {system_metrics['disk']['percent']:.1f}%"
                    )
            if "error" not in app_metrics:
                for endpoint, stats in app_metrics["error_rates"].items():
                    if (
                        stats["error_rate"]
                        > self.default_thresholds["error_rate_percent"]
                    ):
                        health_score -= 10
                        issues.append(
                            f"High error rate for {endpoint}: {stats['error_rate']:.1f}%"
                        )
                for endpoint, stats in app_metrics["response_times"].items():
                    if stats["avg"] > self.default_thresholds["response_time_ms"]:
                        health_score -= 10
                        issues.append(
                            f"Slow response time for {endpoint}: {stats['avg']:.1f}ms"
                        )
            if active_alerts:
                health_score -= len(active_alerts) * 5
                issues.append(f"{len(active_alerts)} active alerts")
            health_score = max(0, health_score)
            if health_score >= 90:
                status = "healthy"
            elif health_score >= 70:
                status = "warning"
            elif health_score >= 50:
                status = "degraded"
            else:
                status = "critical"
            return {
                "status": status,
                "health_score": health_score,
                "issues": issues,
                "system_metrics": system_metrics,
                "application_metrics": app_metrics,
                "active_alerts_count": len(active_alerts),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Health status check failed: {e}")
            return {
                "status": "unknown",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _check_alerts(
        self, metric_name: str, value: float, tags: Dict[str, str] = None
    ) -> Any:
        """Check if metric value triggers any alerts"""
        for alert_name, rule in self.alert_rules.items():
            if rule["metric_name"] != metric_name:
                continue
            if rule["tags"] and tags:
                if not all((tags.get(k) == v for k, v in rule["tags"].items())):
                    continue
            triggered = False
            operator = rule["operator"]
            threshold = rule["threshold"]
            if operator == "gt" and value > threshold:
                triggered = True
            elif operator == "lt" and value < threshold:
                triggered = True
            elif operator == "gte" and value >= threshold:
                triggered = True
            elif operator == "lte" and value <= threshold:
                triggered = True
            elif operator == "eq" and value == threshold:
                triggered = True
            if triggered:
                alert = {
                    "alert_name": alert_name,
                    "metric_name": metric_name,
                    "value": value,
                    "threshold": threshold,
                    "operator": operator,
                    "tags": tags or {},
                    "timestamp": datetime.now(timezone.utc),
                }
                self.alerts.append(alert)
                self.logger.warning(
                    f"Alert triggered: {alert_name} - {metric_name} {operator} {threshold} (actual: {value})"
                )
                if rule["callback"]:
                    try:
                        rule["callback"](alert)
                    except Exception as e:
                        self.logger.error(
                            f"Alert callback failed for {alert_name}: {e}"
                        )

    def _cleanup_old_metrics(self, metric_name: str) -> Any:
        """Remove old metric points"""
        if metric_name not in self.metrics:
            return
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        points = self.metrics[metric_name]
        while points and points[0].timestamp < cutoff_time:
            points.popleft()

    def _start_system_monitoring(self) -> Any:
        """Start background system monitoring"""

        def monitor_system():
            while self.system_metrics_enabled:
                try:
                    system_metrics = self.get_system_metrics()
                    if "error" not in system_metrics:
                        self.record_metric(
                            "system_cpu_percent", system_metrics["cpu"]["percent"]
                        )
                        self.record_metric(
                            "system_memory_percent", system_metrics["memory"]["percent"]
                        )
                        self.record_metric(
                            "system_disk_percent", system_metrics["disk"]["percent"]
                        )
                        self.record_metric(
                            "system_memory_used_bytes", system_metrics["memory"]["used"]
                        )
                        self.record_metric(
                            "system_memory_available_bytes",
                            system_metrics["memory"]["available"],
                        )
                        self.record_metric(
                            "system_disk_used_bytes", system_metrics["disk"]["used"]
                        )
                        self.record_metric(
                            "system_disk_free_bytes", system_metrics["disk"]["free"]
                        )
                    time.sleep(30)
                except Exception as e:
                    self.logger.error(f"System monitoring error: {e}")
                    time.sleep(60)

        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop system monitoring"""
        self.system_metrics_enabled = False

    def reset_metrics(self) -> Any:
        """Reset all metrics and counters"""
        self.metrics.clear()
        self.alerts.clear()
        self.request_counts.clear()
        self.response_times.clear()
        self.error_counts.clear()
        self.logger.info("All metrics reset")


def monitor_performance(monitor: PerformanceMonitor, metric_prefix: str = "") -> Any:
    """Decorator to monitor function performance"""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                metric_name = (
                    f"{metric_prefix}{func.__name__}_duration_ms"
                    if metric_prefix
                    else f"{func.__name__}_duration_ms"
                )
                monitor.record_metric(
                    metric_name, execution_time, {"status": "success"}
                )
                monitor.record_metric(
                    (
                        f"{metric_prefix}{func.__name__}_calls_total"
                        if metric_prefix
                        else f"{func.__name__}_calls_total"
                    ),
                    1,
                    {"status": "success"},
                )
                return result
            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                metric_name = (
                    f"{metric_prefix}{func.__name__}_duration_ms"
                    if metric_prefix
                    else f"{func.__name__}_duration_ms"
                )
                monitor.record_metric(metric_name, execution_time, {"status": "error"})
                monitor.record_metric(
                    (
                        f"{metric_prefix}{func.__name__}_calls_total"
                        if metric_prefix
                        else f"{func.__name__}_calls_total"
                    ),
                    1,
                    {"status": "error"},
                )
                monitor.record_metric(
                    (
                        f"{metric_prefix}{func.__name__}_errors_total"
                        if metric_prefix
                        else f"{func.__name__}_errors_total"
                    ),
                    1,
                    {"error_type": type(e).__name__},
                )
                raise

        return wrapper

    return decorator


def monitor_database_query(monitor: PerformanceMonitor) -> Any:
    """Decorator to monitor database queries"""

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                query_type = "unknown"
                table = "unknown"
                if "select" in func.__name__.lower():
                    query_type = "select"
                elif "insert" in func.__name__.lower():
                    query_type = "insert"
                elif "update" in func.__name__.lower():
                    query_type = "update"
                elif "delete" in func.__name__.lower():
                    query_type = "delete"
                monitor.record_database_query(query_type, table, execution_time)
                return result
            except Exception:
                execution_time = (time.time() - start_time) * 1000
                monitor.record_database_query("error", "unknown", execution_time)
                raise

        return wrapper

    return decorator
