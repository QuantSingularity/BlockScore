"""
Background Job Manager for BlockScore Backend
Celery-based background job processing for scalability
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from celery import Celery, Task
    from celery.result import AsyncResult

    _CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    Task = object
    AsyncResult = None
    _CELERY_AVAILABLE = False


# Module-level Celery instance used by all task decorators
celery_app = Celery("blockscore_jobs") if _CELERY_AVAILABLE else None


class JobManager:
    """Background job manager using Celery"""

    def __init__(self, app_config: Dict[str, Any]) -> None:
        self.config = app_config
        self.logger = logging.getLogger(__name__)
        self.celery = self._create_celery_app()
        self.job_registry = {}

    def _create_celery_app(self) -> Any:
        """Create and configure Celery application"""
        if not _CELERY_AVAILABLE:
            self.logger.warning("Celery not installed; background jobs disabled")
            return None
        celery_config = {
            "broker_url": self.config.get(
                "CELERY_BROKER_URL", "redis://localhost:6379/0"
            ),
            "result_backend": self.config.get(
                "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
            ),
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_time_limit": 30 * 60,
            "task_soft_time_limit": 25 * 60,
            "worker_prefetch_multiplier": 1,
            "task_acks_late": True,
            "worker_disable_rate_limits": False,
            "task_compression": "gzip",
            "result_compression": "gzip",
            "result_expires": 3600,
            "task_routes": {
                "blockscore_jobs.credit_scoring.*": {"queue": "credit_scoring"},
                "blockscore_jobs.blockchain.*": {"queue": "blockchain"},
                "blockscore_jobs.compliance.*": {"queue": "compliance"},
                "blockscore_jobs.notifications.*": {"queue": "notifications"},
                "blockscore_jobs.maintenance.*": {"queue": "maintenance"},
            },
            "beat_schedule": {
                "update-blockchain-transactions": {
                    "task": "blockscore_jobs.blockchain.update_pending_transactions",
                    "schedule": 60.0,
                },
                "cleanup-expired-sessions": {
                    "task": "blockscore_jobs.maintenance.cleanup_expired_sessions",
                    "schedule": 3600.0,
                },
                "generate-compliance-reports": {
                    "task": "blockscore_jobs.compliance.generate_daily_reports",
                    "schedule": 86400.0,
                },
                "monitor-system-health": {
                    "task": "blockscore_jobs.maintenance.system_health_check",
                    "schedule": 300.0,
                },
            },
        }
        celery_app.config_from_object(celery_config)
        return celery_app

    def submit_job(
        self,
        task_name: str,
        args: List = None,
        kwargs: Dict = None,
        queue: str = "default",
        priority: int = 5,
        countdown: int = None,
        eta: datetime = None,
    ) -> str:
        """Submit a background job"""
        try:
            args = args or []
            kwargs = kwargs or {}
            job_id = str(uuid.uuid4())
            task_options = {"task_id": job_id, "queue": queue, "priority": priority}
            if countdown:
                task_options["countdown"] = countdown
            elif eta:
                task_options["eta"] = eta
            self.celery.send_task(task_name, args=args, kwargs=kwargs, **task_options)
            self.job_registry[job_id] = {
                "task_name": task_name,
                "submitted_at": datetime.now(timezone.utc),
                "queue": queue,
                "priority": priority,
                "status": "PENDING",
            }
            self.logger.info(f"Job {job_id} submitted: {task_name}")
            return job_id
        except Exception as e:
            self.logger.error(f"Job submission failed: {e}")
            raise e

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and result"""
        try:
            result = AsyncResult(job_id, app=self.celery)
            job_info = self.job_registry.get(job_id, {})
            status_info = {
                "job_id": job_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
                "traceback": result.traceback if result.failed() else None,
                "submitted_at": job_info.get("submitted_at"),
                "task_name": job_info.get("task_name"),
                "queue": job_info.get("queue"),
            }
            if result.date_done:
                status_info["completed_at"] = result.date_done
                if job_info.get("submitted_at"):
                    duration = result.date_done - job_info["submitted_at"]
                    status_info["duration_seconds"] = duration.total_seconds()
            return status_info
        except Exception as e:
            self.logger.error(f"Job status check failed for {job_id}: {e}")
            return {"job_id": job_id, "status": "UNKNOWN", "error": str(e)}

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job"""
        try:
            result = AsyncResult(job_id, app=self.celery)
            result.revoke(terminate=True)
            if job_id in self.job_registry:
                self.job_registry[job_id]["status"] = "REVOKED"
            self.logger.info(f"Job {job_id} cancelled")
            return True
        except Exception as e:
            self.logger.error(f"Job cancellation failed for {job_id}: {e}")
            return False

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            inspect = self.celery.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            reserved_tasks = inspect.reserved()
            queue_lengths = {}
            try:
                import redis

                redis_client = redis.from_url(self.config.get("CELERY_BROKER_URL"))
                queues = [
                    "default",
                    "credit_scoring",
                    "blockchain",
                    "compliance",
                    "notifications",
                    "maintenance",
                ]
                for queue in queues:
                    queue_lengths[queue] = redis_client.llen(f"celery:{queue}")
            except Exception as e:
                self.logger.warning(f"Could not get queue lengths: {e}")
            return {
                "active_tasks": active_tasks or {},
                "scheduled_tasks": scheduled_tasks or {},
                "reserved_tasks": reserved_tasks or {},
                "queue_lengths": queue_lengths,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Queue stats retrieval failed: {e}")
            return {"error": str(e)}

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        try:
            inspect = self.celery.control.inspect()
            stats = inspect.stats()
            registered_tasks = inspect.registered()
            ping_result = inspect.ping()
            return {
                "worker_stats": stats or {},
                "registered_tasks": registered_tasks or {},
                "worker_ping": ping_result or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Worker stats retrieval failed: {e}")
            return {"error": str(e)}

    def schedule_recurring_job(
        self,
        name: str,
        task_name: str,
        schedule: Dict[str, Any],
        args: List = None,
        kwargs: Dict = None,
    ) -> bool:
        """Schedule a recurring job"""
        try:
            beat_schedule = {
                name: {
                    "task": task_name,
                    "schedule": schedule.get("interval", 3600),
                    "args": args or [],
                    "kwargs": kwargs or {},
                }
            }
            self.celery.conf.beat_schedule.update(beat_schedule)
            self.logger.info(f"Recurring job scheduled: {name}")
            return True
        except Exception as e:
            self.logger.error(f"Recurring job scheduling failed: {e}")
            return False

    def cleanup_completed_jobs(self, older_than_hours: int = 24) -> int:
        """Clean up completed job records"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            cleaned_count = 0
            jobs_to_remove = []
            for job_id, job_info in self.job_registry.items():
                if (
                    job_info.get("submitted_at", datetime.now(timezone.utc))
                    < cutoff_time
                ):
                    result = AsyncResult(job_id, app=self.celery)
                    if result.ready():
                        jobs_to_remove.append(job_id)
                        cleaned_count += 1
            for job_id in jobs_to_remove:
                del self.job_registry[job_id]
            self.logger.info(f"Cleaned up {cleaned_count} completed jobs")
            return cleaned_count
        except Exception as e:
            self.logger.error(f"Job cleanup failed: {e}")
            return 0

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on job system"""
        health = {
            "broker_connected": False,
            "workers_available": False,
            "queues_accessible": False,
            "errors": [],
        }
        try:
            inspect = self.celery.control.inspect()
            ping_result = inspect.ping()
            if ping_result:
                health["broker_connected"] = True
                health["workers_available"] = len(ping_result) > 0
            try:
                queue_stats = self.get_queue_stats()
                health["queues_accessible"] = "error" not in queue_stats
            except Exception as e:
                health["errors"].append(f"Queue check failed: {e}")
            try:
                test_job_id = self.submit_job(
                    "blockscore_jobs.test.ping", queue="default"
                )
                test_result = self.get_job_status(test_job_id)
                health["test_job_submitted"] = test_result["status"] in [
                    "PENDING",
                    "SUCCESS",
                ]
            except Exception as e:
                health["errors"].append(f"Test job failed: {e}")
                health["test_job_submitted"] = False
        except Exception as e:
            health["errors"].append(f"Health check failed: {e}")
        return health


class BaseTask(Task):
    """Base task class with common functionality"""

    def on_failure(
        self, exc: Any, task_id: Any, args: Any, kwargs: Any, einfo: Any
    ) -> Any:
        """Handle task failure"""
        logging.error(f"Task {task_id} failed: {exc}")

    def on_success(self, retval: Any, task_id: Any, args: Any, kwargs: Any) -> Any:
        """Handle task success"""
        logging.info(f"Task {task_id} completed successfully")

    def on_retry(
        self, exc: Any, task_id: Any, args: Any, kwargs: Any, einfo: Any
    ) -> Any:
        """Handle task retry"""
        logging.warning(f"Task {task_id} retrying due to: {exc}")


if celery_app is not None:

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.credit_scoring.calculate_score"
    )
    def calculate_credit_score_async(
        self, user_id: str, wallet_address: Optional[str] = None
    ) -> Any:
        """Asynchronous credit score calculation"""
        try:
            from models import db
            from services.credit_service import CreditScoringService

            credit_service = CreditScoringService(db)
            result = credit_service.calculate_credit_score(
                user_id, wallet_address, force_recalculation=True
            )
            return {
                "user_id": user_id,
                "credit_score": result.get("score"),
                "calculated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self.retry(exc=exc, countdown=60, max_retries=3)

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.credit_scoring.batch_calculate"
    )
    def batch_calculate_credit_scores(self, user_ids: List[str]) -> Any:
        """Batch credit score calculation"""
        results = []
        for user_id in user_ids:
            try:
                result = calculate_credit_score_async.delay(user_id)
                results.append({"user_id": user_id, "job_id": result.id})
            except Exception as e:
                results.append({"user_id": user_id, "error": str(e)})
        return results

    @celery_app.task(
        bind=True,
        base=BaseTask,
        name="blockscore_jobs.blockchain.update_pending_transactions",
    )
    def update_pending_transactions(self) -> Any:
        """Update pending blockchain transactions"""
        try:
            from services.blockchain_service import BlockchainService

            blockchain_service = BlockchainService({})
            result = blockchain_service.monitor_pending_transactions()
            return result
        except Exception as exc:
            self.retry(exc=exc, countdown=120, max_retries=5)

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.blockchain.submit_transaction"
    )
    def submit_blockchain_transaction(
        self, transaction_type: str, transaction_data: Dict[str, Any]
    ) -> Any:
        """Submit blockchain transaction"""
        try:
            from services.blockchain_service import BlockchainService

            blockchain_service = BlockchainService({})
            if transaction_type == "credit_score_update":
                result = blockchain_service.submit_credit_score_update(
                    **transaction_data
                )
            elif transaction_type == "loan_agreement":
                result = blockchain_service.submit_loan_agreement(**transaction_data)
            elif transaction_type == "payment_record":
                result = blockchain_service.record_payment(**transaction_data)
            else:
                raise ValueError(f"Unknown transaction type: {transaction_type}")
            return result
        except Exception as exc:
            self.retry(exc=exc, countdown=180, max_retries=3)

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.compliance.kyc_assessment"
    )
    def perform_kyc_assessment(self, user_id: str, kyc_level: str = "basic") -> Any:
        """Perform KYC assessment"""
        try:
            from models import db
            from services.compliance_service import ComplianceService

            compliance_service = ComplianceService(db)
            result = compliance_service.perform_kyc_assessment(user_id, kyc_level)
            return result
        except Exception as exc:
            self.retry(exc=exc, countdown=60, max_retries=3)

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.compliance.aml_screening"
    )
    def perform_aml_screening(
        self, user_id: str, transaction_data: Dict[str, Any] = None
    ) -> Any:
        """Perform AML screening"""
        try:
            from models import db
            from services.compliance_service import ComplianceService

            compliance_service = ComplianceService(db)
            result = compliance_service.perform_aml_screening(user_id, transaction_data)
            return result
        except Exception as exc:
            self.retry(exc=exc, countdown=60, max_retries=3)

    @celery_app.task(
        bind=True,
        base=BaseTask,
        name="blockscore_jobs.compliance.generate_daily_reports",
    )
    def generate_daily_compliance_reports(self) -> Any:
        """Generate daily compliance reports"""
        try:
            from models import db
            from services.compliance_service import ComplianceService

            compliance_service = ComplianceService(db)
            end_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            start_date = end_date - timedelta(days=1)
            report = compliance_service.generate_compliance_report(
                start_date, end_date
            )
            return {
                "report_date": start_date.date().isoformat(),
                "summary": report.get("summary", {}),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self.retry(exc=exc, countdown=300, max_retries=2)

    @celery_app.task(
        bind=True,
        base=BaseTask,
        name="blockscore_jobs.maintenance.cleanup_expired_sessions",
    )
    def cleanup_expired_sessions(self) -> Any:
        """Clean up expired user sessions"""
        try:
            from models import db
            from models.user import UserSession

            cutoff_time = datetime.now(timezone.utc)
            expired_sessions = UserSession.query.filter(
                UserSession.expires_at < cutoff_time
            ).all()
            count = len(expired_sessions)
            for session in expired_sessions:
                db.session.delete(session)
            db.session.commit()
            return {
                "cleaned_sessions": count,
                "cleaned_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self.retry(exc=exc, countdown=300, max_retries=2)

    @celery_app.task(
        bind=True, base=BaseTask, name="blockscore_jobs.maintenance.system_health_check"
    )
    def system_health_check(self) -> Any:
        """Perform system health check"""
        try:
            from models import db
            from utils.database import DatabaseOptimizer

            db_optimizer = DatabaseOptimizer(db, db.engine)
            db_health = db_optimizer.get_database_health()
            cache_health = {"available": False}
            blockchain_health = {"connected": False}
            health_report = {
                "database": db_health,
                "cache": cache_health,
                "blockchain": blockchain_health,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            if db_health.get("connection_status") != "connected":
                logging.critical("Database connection issue detected")
            return health_report
        except Exception as exc:
            logging.error(f"Health check failed: {exc}")
            self.retry(exc=exc, countdown=60, max_retries=2)

    @celery_app.task(bind=True, base=BaseTask, name="blockscore_jobs.test.ping")
    def ping_task(self) -> Any:
        """Simple ping task for testing"""
        return {"message": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}

else:
    # Celery unavailable: define no-op stubs so imports don't fail
    def calculate_credit_score_async(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; calculate_credit_score_async is a no-op")

    def batch_calculate_credit_scores(*args: Any, **kwargs: Any) -> None:
        logging.warning(
            "Celery unavailable; batch_calculate_credit_scores is a no-op"
        )

    def update_pending_transactions(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; update_pending_transactions is a no-op")

    def submit_blockchain_transaction(*args: Any, **kwargs: Any) -> None:
        logging.warning(
            "Celery unavailable; submit_blockchain_transaction is a no-op"
        )

    def perform_kyc_assessment(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; perform_kyc_assessment is a no-op")

    def perform_aml_screening(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; perform_aml_screening is a no-op")

    def generate_daily_compliance_reports(*args: Any, **kwargs: Any) -> None:
        logging.warning(
            "Celery unavailable; generate_daily_compliance_reports is a no-op"
        )

    def cleanup_expired_sessions(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; cleanup_expired_sessions is a no-op")

    def system_health_check(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; system_health_check is a no-op")

    def ping_task(*args: Any, **kwargs: Any) -> None:
        logging.warning("Celery unavailable; ping_task is a no-op")