import compat_stubs  # noqa

"""
Database Optimizer for BlockScore Backend
Database performance optimization and monitoring utilities
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from sqlalchemy import inspect, text
    from sqlalchemy.engine import Engine
except ImportError:
    inspect = None
    text = lambda s: s
    Engine = object


class DatabaseOptimizer:
    """Database performance optimization and monitoring"""

    def __init__(self, db: Any, engine: Engine) -> None:
        self.db = db
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        self.query_stats = {}
        self.slow_query_threshold = 1.0

    def analyze_query_performance(
        self, query: str, params: Dict = None
    ) -> Dict[str, Any]:
        """Analyze query performance"""
        try:
            start_time = time.time()
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                rows = result.fetchall()
            end_time = time.time()
            execution_time = end_time - start_time
            plan = self._get_query_plan(query, params)
            analysis = {
                "query": query,
                "execution_time": execution_time,
                "row_count": len(rows),
                "is_slow": execution_time > self.slow_query_threshold,
                "query_plan": plan,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            query_hash = hash(query)
            if query_hash not in self.query_stats:
                self.query_stats[query_hash] = {
                    "query": query,
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "max_time": 0,
                    "min_time": float("inf"),
                }
            stats = self.query_stats[query_hash]
            stats["count"] += 1
            stats["total_time"] += execution_time
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["max_time"] = max(stats["max_time"], execution_time)
            stats["min_time"] = min(stats["min_time"], execution_time)
            return analysis
        except Exception as e:
            self.logger.error(f"Query analysis failed: {e}")
            return {"error": str(e)}

    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries"""
        slow_queries = []
        for stats in self.query_stats.values():
            if stats["avg_time"] > self.slow_query_threshold:
                slow_queries.append(stats)
        slow_queries.sort(key=lambda x: x["avg_time"], reverse=True)
        return slow_queries[:limit]

    def analyze_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """Analyze table statistics"""
        try:
            with self.engine.connect() as conn:
                size_query = text(
                    "\n                    SELECT\n                        pg_size_pretty(pg_total_relation_size(:table_name)) as total_size,\n                        pg_size_pretty(pg_relation_size(:table_name)) as table_size,\n                        pg_size_pretty(pg_total_relation_size(:table_name) - pg_relation_size(:table_name)) as index_size\n                "
                )
                size_result = conn.execute(
                    size_query, {"table_name": table_name}
                ).fetchone()
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                row_count = conn.execute(count_query).scalar()
                stats_query = text(
                    "\n                    SELECT\n                        schemaname,\n                        tablename,\n                        attname,\n                        n_distinct,\n                        most_common_vals,\n                        most_common_freqs,\n                        histogram_bounds\n                    FROM pg_stats\n                    WHERE tablename = :table_name\n                "
                )
                column_stats = conn.execute(
                    stats_query, {"table_name": table_name}
                ).fetchall()
                return {
                    "table_name": table_name,
                    "row_count": row_count,
                    "total_size": size_result[0] if size_result else "Unknown",
                    "table_size": size_result[1] if size_result else "Unknown",
                    "index_size": size_result[2] if size_result else "Unknown",
                    "column_statistics": [dict(row._mapping) for row in column_stats],
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Table analysis failed for {table_name}: {e}")
            return {"error": str(e)}

    def check_index_usage(self, table_name: str) -> Dict[str, Any]:
        """Check index usage statistics"""
        try:
            with self.engine.connect() as conn:
                index_query = text(
                    "\n                    SELECT\n                        schemaname,\n                        tablename,\n                        indexname,\n                        idx_tup_read,\n                        idx_tup_fetch,\n                        idx_scan,\n                        CASE\n                            WHEN idx_scan = 0 THEN 'Never used'\n                            WHEN idx_scan < 100 THEN 'Rarely used'\n                            WHEN idx_scan < 1000 THEN 'Moderately used'\n                            ELSE 'Frequently used'\n                        END as usage_level\n                    FROM pg_stat_user_indexes\n                    WHERE tablename = :table_name\n                    ORDER BY idx_scan DESC\n                "
                )
                indexes = conn.execute(
                    index_query, {"table_name": table_name}
                ).fetchall()
                unused_query = text(
                    "\n                    SELECT\n                        schemaname,\n                        tablename,\n                        indexname,\n                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size\n                    FROM pg_stat_user_indexes\n                    WHERE tablename = :table_name AND idx_scan = 0\n                "
                )
                unused_indexes = conn.execute(
                    unused_query, {"table_name": table_name}
                ).fetchall()
                return {
                    "table_name": table_name,
                    "indexes": [dict(row._mapping) for row in indexes],
                    "unused_indexes": [dict(row._mapping) for row in unused_indexes],
                    "total_indexes": len(indexes),
                    "unused_count": len(unused_indexes),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Index usage check failed for {table_name}: {e}")
            return {"error": str(e)}

    def suggest_indexes(
        self, table_name: str, query_patterns: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Suggest indexes based on query patterns"""
        suggestions = []
        try:
            inspector = inspect(self.engine)
            existing_indexes = inspector.get_indexes(table_name)
            existing_columns = set()
            for index in existing_indexes:
                existing_columns.update(index["column_names"])
            columns = inspector.get_columns(table_name)
            for column in columns:
                col_name = column["name"]
                col_type = str(column["type"])
                if col_name not in existing_columns:
                    if col_name.endswith("_id"):
                        suggestions.append(
                            {
                                "type": "single_column",
                                "columns": [col_name],
                                "reason": "Foreign key column",
                                "priority": "high",
                                "sql": f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name} ({col_name});",
                            }
                        )
                    if col_name in [
                        "email",
                        "username",
                        "status",
                        "type",
                        "created_at",
                        "updated_at",
                    ]:
                        suggestions.append(
                            {
                                "type": "single_column",
                                "columns": [col_name],
                                "reason": "Commonly filtered column",
                                "priority": "medium",
                                "sql": f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name} ({col_name});",
                            }
                        )
                    if "timestamp" in col_type.lower() or "date" in col_type.lower():
                        suggestions.append(
                            {
                                "type": "single_column",
                                "columns": [col_name],
                                "reason": "Date/timestamp column for range queries",
                                "priority": "medium",
                                "sql": f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name} ({col_name});",
                            }
                        )
            if table_name == "users":
                suggestions.append(
                    {
                        "type": "composite",
                        "columns": ["email", "status"],
                        "reason": "Login queries often filter by email and status",
                        "priority": "high",
                        "sql": f"CREATE INDEX idx_{table_name}_email_status ON {table_name} (email, status);",
                    }
                )
            elif table_name == "credit_scores":
                suggestions.append(
                    {
                        "type": "composite",
                        "columns": ["user_id", "calculated_at"],
                        "reason": "Queries often need latest score for user",
                        "priority": "high",
                        "sql": f"CREATE INDEX idx_{table_name}_user_calculated ON {table_name} (user_id, calculated_at DESC);",
                    }
                )
            elif table_name == "audit_logs":
                suggestions.append(
                    {
                        "type": "composite",
                        "columns": ["user_id", "event_timestamp"],
                        "reason": "Audit queries often filter by user and time range",
                        "priority": "high",
                        "sql": f"CREATE INDEX idx_{table_name}_user_timestamp ON {table_name} (user_id, event_timestamp DESC);",
                    }
                )
            return suggestions
        except Exception as e:
            self.logger.error(f"Index suggestion failed for {table_name}: {e}")
            return []

    def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """Perform table optimization"""
        results = {
            "table_name": table_name,
            "actions_performed": [],
            "recommendations": [],
            "errors": [],
        }
        try:
            with self.engine.connect() as conn:
                try:
                    conn.execute(text(f"ANALYZE {table_name}"))
                    results["actions_performed"].append("Updated table statistics")
                except Exception as e:
                    results["errors"].append(f"Statistics update failed: {e}")
                bloat_query = text(
                    "\n                    SELECT\n                        schemaname,\n                        tablename,\n                        n_dead_tup,\n                        n_live_tup,\n                        CASE\n                            WHEN n_live_tup > 0 THEN (n_dead_tup::float / n_live_tup::float) * 100\n                            ELSE 0\n                        END as dead_tuple_percent\n                    FROM pg_stat_user_tables\n                    WHERE tablename = :table_name\n                "
                )
                bloat_result = conn.execute(
                    bloat_query, {"table_name": table_name}
                ).fetchone()
                if bloat_result and bloat_result[4] > 20:
                    results["recommendations"].append(
                        {
                            "action": "VACUUM",
                            "reason": f"Table has {bloat_result[4]:.1f}% dead tuples",
                            "sql": f"VACUUM {table_name};",
                        }
                    )
                index_suggestions = self.suggest_indexes(table_name)
                if index_suggestions:
                    results["recommendations"].extend(index_suggestions)
                conn.commit()
        except Exception as e:
            results["errors"].append(f"Optimization failed: {e}")
        return results

    def get_database_health(self) -> Dict[str, Any]:
        """Get overall database health metrics"""
        health = {
            "connection_status": "unknown",
            "active_connections": 0,
            "database_size": "unknown",
            "slow_queries": 0,
            "cache_hit_ratio": 0,
            "errors": [],
        }
        try:
            with self.engine.connect() as conn:
                health["connection_status"] = "connected"
                conn_query = text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                health["active_connections"] = conn.execute(conn_query).scalar()
                size_query = text(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                health["database_size"] = conn.execute(size_query).scalar()
                cache_query = text(
                    "\n                    SELECT\n                        round(\n                            (sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read))) * 100, 2\n                        ) as cache_hit_ratio\n                    FROM pg_statio_user_tables\n                "
                )
                cache_result = conn.execute(cache_query).scalar()
                health["cache_hit_ratio"] = cache_result or 0
                health["slow_queries"] = len(self.get_slow_queries())
                lock_query = text(
                    "\n                    SELECT count(*)\n                    FROM pg_locks\n                    WHERE NOT granted\n                "
                )
                health["blocked_queries"] = conn.execute(lock_query).scalar()
        except Exception as e:
            health["connection_status"] = "error"
            health["errors"].append(str(e))
        return health

    def monitor_connections(self) -> Dict[str, Any]:
        """Monitor database connections"""
        try:
            with self.engine.connect() as conn:
                conn_query = text(
                    "\n                    SELECT\n                        state,\n                        count(*) as count,\n                        avg(extract(epoch from (now() - query_start))) as avg_duration\n                    FROM pg_stat_activity\n                    WHERE datname = current_database()\n                    GROUP BY state\n                "
                )
                connections = conn.execute(conn_query).fetchall()
                long_query = text(
                    "\n                    SELECT\n                        pid,\n                        usename,\n                        application_name,\n                        state,\n                        query_start,\n                        extract(epoch from (now() - query_start)) as duration,\n                        left(query, 100) as query_preview\n                    FROM pg_stat_activity\n                    WHERE datname = current_database()\n                        AND state = 'active'\n                        AND query_start < now() - interval '30 seconds'\n                    ORDER BY query_start\n                "
                )
                long_queries = conn.execute(long_query).fetchall()
                return {
                    "connection_summary": [dict(row._mapping) for row in connections],
                    "long_running_queries": [
                        dict(row._mapping) for row in long_queries
                    ],
                    "total_connections": sum((row[1] for row in connections)),
                    "monitored_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as e:
            self.logger.error(f"Connection monitoring failed: {e}")
            return {"error": str(e)}

    def _get_query_plan(
        self, query: str, params: Optional[Dict] = None
    ) -> Optional[List[Dict]]:
        """Get query execution plan"""
        try:
            with self.engine.connect() as conn:
                explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query}"
                if params:
                    result = conn.execute(text(explain_query), params)
                else:
                    result = conn.execute(text(explain_query))
                plan = result.fetchone()[0]
                return plan
        except Exception as e:
            self.logger.error(f"Query plan retrieval failed: {e}")
            return None

    @contextmanager
    def query_profiler(self, query_name: str = "unnamed") -> Any:
        """Context manager for profiling queries"""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            if execution_time > self.slow_query_threshold:
                self.logger.warning(
                    f"Slow query detected: {query_name} took {execution_time:.3f}s"
                )

    def create_maintenance_plan(self) -> Dict[str, Any]:
        """Create database maintenance plan"""
        plan = {
            "daily_tasks": [
                "Update table statistics (ANALYZE)",
                "Monitor slow queries",
                "Check connection pool usage",
            ],
            "weekly_tasks": [
                "VACUUM tables with high dead tuple ratio",
                "Review index usage statistics",
                "Check database size growth",
            ],
            "monthly_tasks": [
                "Full database VACUUM ANALYZE",
                "Review and optimize slow queries",
                "Evaluate index effectiveness",
                "Archive old audit logs",
            ],
            "recommendations": [],
        }
        health = self.get_database_health()
        if health["cache_hit_ratio"] < 95:
            plan["recommendations"].append(
                "Consider increasing shared_buffers for better cache hit ratio"
            )
        if health["slow_queries"] > 10:
            plan["recommendations"].append("Review and optimize slow queries")
        slow_queries = self.get_slow_queries(5)
        if slow_queries:
            plan["recommendations"].append(
                f"Focus on optimizing {len(slow_queries)} slow queries"
            )
        return plan

    def reset_stats(self) -> Any:
        """Reset query statistics"""
        self.query_stats.clear()
        self.logger.info("Query statistics reset")
