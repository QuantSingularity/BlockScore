MIN_SCORE = 300
MAX_SCORE = 850
NEUTRAL_SCORE = 500
MAX_RECORDS = 1000
SECONDS_PER_DAY = 86400.0

FEATURE_COLUMNS = [
    "payment_ratio",
    "late_ratio",
    "loan_count",
    "log_avg_loan",
    "log_total_borrowed",
    "outstanding_ratio",
    "avg_repayment_days",
    "history_days",
    "impact_sum",
]

REPAYABLE_TYPES = frozenset({"loan", "payment"})
TRUE_VALUES = frozenset({"true", "1", "yes", "y"})
