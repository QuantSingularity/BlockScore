import {
  Box,
  Grid,
  LinearProgress,
  Paper,
  Typography,
  useTheme,
} from "@mui/material";

const CreditFactors = ({ features }) => {
  const theme = useTheme();

  // Default values if no features provided
  const defaultFeatures = {
    total_loans: 0,
    total_amount: 0,
    repaid_ratio: 0,
    avg_loan_amount: 0,
  };

  const data = features || defaultFeatures;

  // Calculate normalized values for progress bars (0-100)
  const normalizedRepaidRatio = data.repaid_ratio * 100;
  const normalizedTotalLoans = Math.min((data.total_loans / 10) * 100, 100); // Assuming 10+ loans is max
  const normalizedAvgAmount = Math.min(
    (data.avg_loan_amount / 5000) * 100,
    100,
  ); // Assuming $5000+ is max

  // Get color based on value
  const getColorForValue = (value) => {
    if (value >= 80) return theme.palette.success.main;
    if (value >= 60) return theme.palette.primary.main;
    if (value >= 40) return theme.palette.info.main;
    if (value >= 20) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  return (
    <Box>
      <Grid container spacing={2}>
        {/* Repayment History */}
        <Grid item xs={12}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 2,
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Repayment History
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Box sx={{ width: "100%", mr: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={normalizedRepaidRatio}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: theme.palette.grey[200],
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: getColorForValue(normalizedRepaidRatio),
                    },
                  }}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {normalizedRepaidRatio.toFixed(0)}%
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              {data.repaid_ratio < 0.6 ? "Needs improvement" : "Good standing"}
            </Typography>
          </Paper>
        </Grid>

        {/* Loan Count */}
        <Grid item xs={12}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 2,
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Loan Count
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Box sx={{ width: "100%", mr: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={normalizedTotalLoans}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: theme.palette.grey[200],
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: getColorForValue(normalizedTotalLoans),
                    },
                  }}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                {data.total_loans}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              {data.total_loans < 3 ? "Limited history" : "Established history"}
            </Typography>
          </Paper>
        </Grid>

        {/* Average Loan Amount */}
        <Grid item xs={12}>
          <Paper
            elevation={0}
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 2,
            }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Average Loan Amount
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Box sx={{ width: "100%", mr: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={normalizedAvgAmount}
                  sx={{
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: theme.palette.grey[200],
                    "& .MuiLinearProgress-bar": {
                      backgroundColor: getColorForValue(normalizedAvgAmount),
                    },
                  }}
                />
              </Box>
              <Typography variant="body2" color="text.secondary">
                ${data.avg_loan_amount.toFixed(0)}
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary">
              {data.avg_loan_amount < 1000 ? "Small loans" : "Moderate loans"}
            </Typography>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CreditFactors;
