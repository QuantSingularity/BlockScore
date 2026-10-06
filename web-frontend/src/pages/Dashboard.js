import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  Typography,
} from "@mui/material";
import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import CreditFactors from "../components/dashboard/CreditFactors";
import CreditScoreGauge from "../components/dashboard/CreditScoreGauge";
import QuickActions from "../components/dashboard/QuickActions";
import ScoreInsights from "../components/dashboard/ScoreInsights";
import TransactionHistory from "../components/dashboard/TransactionHistory";
import { useAuth } from "../contexts/AuthContext";
import { useCredit } from "../contexts/CreditContext";
const gradeColor = {
  Excellent: "success",
  "Very Good": "success",
  Good: "primary",
  Fair: "warning",
  Poor: "error",
};
const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    creditData,
    history,
    loading,
    error,
    needsWallet,
    recalculateCreditScore,
  } = useCredit();
  const [recalculating, setRecalculating] = useState(false);
  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      await recalculateCreditScore();
    } catch {
      return;
    } finally {
      setRecalculating(false);
    }
  };
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
      transition={{ duration: 0.4 }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="overline"
          sx={{ color: "text.secondary", fontWeight: 700, letterSpacing: 1.4 }}
        >
          Dashboard
        </Typography>
        <Typography
          variant="h4"
          component="h1"
          sx={{ fontWeight: 600, mt: 0.5 }}
        >
          Welcome back{user?.email ? `, ${user.email}` : ""}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          Here&rsquo;s your current credit status and history.
        </Typography>
      </Box>

      {needsWallet && (
        <Alert
          severity="info"
          sx={{ mb: 3 }}
          action={
            <Button
              color="inherit"
              size="small"
              onClick={() => navigate("/profile")}
            >
              Add wallet
            </Button>
          }
        >
          Add a wallet address to your profile to calculate your credit score.
        </Alert>
      )}

      {error && !needsWallet && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.05 }}
            style={{ height: "100%" }}
          >
            <Card sx={{ height: "100%", overflow: "hidden" }}>
              <Box
                sx={{
                  px: 3,
                  py: 2,
                  backgroundColor: "#0D1220",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <Typography sx={{ color: "white", fontWeight: 600 }}>
                  Your Credit Score
                </Typography>
                <Chip
                  size="small"
                  label={creditData?.score_grade || "Not available"}
                  color={gradeColor[creditData?.score_grade] || "default"}
                  sx={{
                    fontWeight: 600,
                    ...(gradeColor[creditData?.score_grade]
                      ? {}
                      : {
                          bgcolor: "rgba(255,255,255,0.12)",
                          color: "rgba(255,255,255,0.8)",
                        }),
                  }}
                />
              </Box>

              <Box
                sx={{
                  p: 3,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
              >
                <Box sx={{ my: 1, width: "100%", maxWidth: 260 }}>
                  <CreditScoreGauge score={creditData?.score || 0} />
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  align="center"
                >
                  {creditData?.calculated_at
                    ? `Last updated ${new Date(
                        creditData.calculated_at,
                      ).toLocaleDateString()}`
                    : "Not calculated yet"}
                </Typography>

                <Divider sx={{ width: "100%", my: 2.5 }} />

                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<RefreshRoundedIcon />}
                  onClick={handleRecalculate}
                  disabled={recalculating}
                >
                  {recalculating ? "Recalculating..." : "Recalculate score"}
                </Button>
              </Box>
            </Card>
          </motion.div>
        </Grid>

        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            style={{ height: "100%" }}
          >
            <CreditFactors scoreBreakdown={creditData?.score_breakdown} />
          </motion.div>
        </Grid>

        <Grid item xs={12} md={6} lg={4}>
          <motion.div
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            style={{ height: "100%" }}
          >
            <Card sx={{ height: "100%", p: 3 }}>
              <Typography sx={{ fontWeight: 600, mb: 2 }}>
                Quick actions
              </Typography>
              <QuickActions />
            </Card>
          </motion.div>
        </Grid>

        {creditData?.scoring_source && (
          <Grid item xs={12}>
            <motion.div
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.18 }}
            >
              <ScoreInsights creditData={creditData} />
            </motion.div>
          </Grid>
        )}

        <Grid item xs={12}>
          <motion.div
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <TransactionHistory history={history} />
          </motion.div>
        </Grid>
      </Grid>
    </motion.div>
  );
};
export default Dashboard;
