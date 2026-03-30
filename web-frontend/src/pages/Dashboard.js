import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Typography,
  useTheme,
} from "@mui/material";
import { motion } from "framer-motion";
import CreditFactors from "../components/dashboard/CreditFactors";
// Components
import CreditScoreGauge from "../components/dashboard/CreditScoreGauge";
import QuickActions from "../components/dashboard/QuickActions";
import TransactionHistory from "../components/dashboard/TransactionHistory";
import { useAuth } from "../contexts/AuthContext";
import { useCredit } from "../contexts/CreditContext";
import { useWeb3 } from "../contexts/Web3Context";

const Dashboard = () => {
  const _theme = useTheme();
  const { user } = useAuth();
  const { accounts } = useWeb3();
  const { creditData, loading, error, fetchCreditScore } = useCredit();

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "80vh",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome back! Here's your current credit status and history.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Credit Score Card */}
        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card sx={{ height: "100%" }}>
              <CardContent
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  p: 3,
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Your Credit Score
                </Typography>

                <Box sx={{ my: 2, width: "100%", maxWidth: 250 }}>
                  <CreditScoreGauge score={creditData?.score || 0} />
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  align="center"
                >
                  Last updated: {new Date().toLocaleDateString()}
                </Typography>

                <Divider sx={{ width: "100%", my: 2 }} />

                <Box sx={{ width: "100%" }}>
                  <Typography variant="body2" gutterBottom>
                    Score Category:
                  </Typography>
                  <Chip
                    label={
                      creditData?.score >= 750
                        ? "Excellent"
                        : creditData?.score >= 700
                          ? "Good"
                          : creditData?.score >= 650
                            ? "Fair"
                            : creditData?.score >= 600
                              ? "Poor"
                              : "Very Poor"
                    }
                    color={
                      creditData?.score >= 750
                        ? "success"
                        : creditData?.score >= 700
                          ? "primary"
                          : creditData?.score >= 650
                            ? "info"
                            : creditData?.score >= 600
                              ? "warning"
                              : "error"
                    }
                    sx={{ fontWeight: 500 }}
                  />
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Credit Factors */}
        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Credit Factors
                </Typography>

                <CreditFactors features={creditData?.features} />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>

                <QuickActions />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Transaction History */}
        <Grid item xs={12}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Transaction History
                </Typography>

                <TransactionHistory history={creditData?.history || []} />
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>
    </motion.div>
  );
};

export default Dashboard;
