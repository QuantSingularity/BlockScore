import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  Paper,
  Slider,
  Typography,
  useTheme,
} from "@mui/material";
import {
  ArcElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
} from "chart.js";
import { motion } from "framer-motion";
import { useState } from "react";
import { Doughnut, Line } from "react-chartjs-2";
import { useAuth } from "../contexts/AuthContext";
import { useWeb3 } from "../contexts/Web3Context";
import { calculateLoan } from "../utils/api";

ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
);

const LoanCalculator = () => {
  const theme = useTheme();
  const { user } = useAuth();
  const { accounts } = useWeb3();

  const [loading, setLoading] = useState(false);
  const [amount, setAmount] = useState(5000);
  const [rate, setRate] = useState(5);
  const [term, setTerm] = useState(36);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const calculateLoanEligibility = async () => {
    try {
      setLoading(true);
      setError(null);

      // Use the wallet address from context if available, otherwise use demo address
      const walletAddress =
        accounts[0] ||
        user?.address ||
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";

      // Use the API service to calculate loan eligibility
      const data = await calculateLoan(walletAddress, amount, rate);
      setResult(data);
    } catch (err) {
      console.error("Error calculating loan:", err);
      setError("Failed to calculate loan eligibility. Please try again later.");

      // For demo purposes, set mock data if API fails
      setResult({
        approval_probability: 75.5,
        monthly_payment: 149.85,
        credit_score: 720,
        loan_term: 36,
        total_payment: 5394.6,
      });
    } finally {
      setLoading(false);
    }
  };

  // Calculate payment schedule
  const generatePaymentSchedule = () => {
    if (!result) return [];

    const monthlyPayment = result.monthly_payment;
    const schedule = [];
    let remainingBalance = amount;
    let totalInterest = 0;

    for (let month = 1; month <= term; month++) {
      const interestPayment = remainingBalance * (rate / 100 / 12);
      const principalPayment = monthlyPayment - interestPayment;
      totalInterest += interestPayment;
      remainingBalance -= principalPayment;

      schedule.push({
        month,
        payment: monthlyPayment,
        principal: principalPayment,
        interest: interestPayment,
        totalInterest,
        balance: Math.max(0, remainingBalance),
      });
    }

    return schedule;
  };

  // Prepare chart data
  const paymentSchedule = generatePaymentSchedule();
  const chartData = {
    labels: paymentSchedule.slice(0, 12).map((item) => `Month ${item.month}`),
    datasets: [
      {
        label: "Principal",
        data: paymentSchedule.slice(0, 12).map((item) => item.principal),
        backgroundColor: theme.palette.primary.main,
        borderColor: theme.palette.primary.main,
      },
      {
        label: "Interest",
        data: paymentSchedule.slice(0, 12).map((item) => item.interest),
        backgroundColor: theme.palette.secondary.main,
        borderColor: theme.palette.secondary.main,
      },
    ],
  };

  // Approval probability chart
  const approvalChartData = {
    labels: ["Approval", "Rejection"],
    datasets: [
      {
        data: result
          ? [result.approval_probability, 100 - result.approval_probability]
          : [50, 50],
        backgroundColor: [theme.palette.success.main, theme.palette.grey[300]],
        borderWidth: 0,
      },
    ],
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
          Loan Calculator
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Estimate your loan eligibility and monthly payments based on your
          credit score.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Loan Parameters */}
        <Grid item xs={12} md={6}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Loan Parameters
                </Typography>

                <Box sx={{ mt: 3 }}>
                  <Typography gutterBottom>
                    Loan Amount: ${amount.toLocaleString()}
                  </Typography>
                  <Slider
                    value={amount}
                    onChange={(_e, newValue) => setAmount(newValue)}
                    min={1000}
                    max={50000}
                    step={500}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `$${value.toLocaleString()}`}
                    sx={{ mb: 4 }}
                  />

                  <Typography gutterBottom>Interest Rate: {rate}%</Typography>
                  <Slider
                    value={rate}
                    onChange={(_e, newValue) => setRate(newValue)}
                    min={1}
                    max={20}
                    step={0.1}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `${value}%`}
                    sx={{ mb: 4 }}
                  />

                  <Typography gutterBottom>Loan Term: {term} months</Typography>
                  <Slider
                    value={term}
                    onChange={(_e, newValue) => setTerm(newValue)}
                    min={12}
                    max={60}
                    step={12}
                    marks={[
                      { value: 12, label: "1 yr" },
                      { value: 24, label: "2 yr" },
                      { value: 36, label: "3 yr" },
                      { value: 48, label: "4 yr" },
                      { value: 60, label: "5 yr" },
                    ]}
                    valueLabelDisplay="auto"
                    valueLabelFormat={(value) => `${value} months`}
                    sx={{ mb: 4 }}
                  />

                  <Button
                    variant="contained"
                    fullWidth
                    size="large"
                    onClick={calculateLoanEligibility}
                    disabled={loading}
                    sx={{ mt: 2 }}
                  >
                    {loading ? <CircularProgress size={24} /> : "Calculate"}
                  </Button>

                  {error && (
                    <Typography color="error" sx={{ mt: 2 }}>
                      {error}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Results */}
        <Grid item xs={12} md={6}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card sx={{ height: "100%" }}>
              <CardContent
                sx={{
                  p: 3,
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Loan Eligibility Results
                </Typography>

                {!result ? (
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexGrow: 1,
                    }}
                  >
                    <Typography color="text.secondary">
                      Adjust parameters and click Calculate to see results
                    </Typography>
                  </Box>
                ) : (
                  <Box sx={{ mt: 2, flexGrow: 1 }}>
                    <Grid container spacing={3}>
                      <Grid item xs={12} sm={6}>
                        <Box
                          sx={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            mb: 3,
                          }}
                        >
                          <Typography
                            variant="subtitle2"
                            color="text.secondary"
                            gutterBottom
                          >
                            Approval Probability
                          </Typography>
                          <Box sx={{ width: 150, height: 150 }}>
                            <Doughnut
                              data={approvalChartData}
                              options={{
                                cutout: "70%",
                                plugins: {
                                  legend: {
                                    display: false,
                                  },
                                  tooltip: {
                                    callbacks: {
                                      label: (context) =>
                                        `${context.label}: ${context.raw}%`,
                                    },
                                  },
                                },
                              }}
                            />
                          </Box>
                          <Typography
                            variant="h5"
                            sx={{
                              mt: 2,
                              fontWeight: 600,
                              color:
                                result.approval_probability > 70
                                  ? "success.main"
                                  : result.approval_probability > 50
                                    ? "primary.main"
                                    : "warning.main",
                            }}
                          >
                            {result.approval_probability.toFixed(1)}%
                          </Typography>
                        </Box>
                      </Grid>

                      <Grid item xs={12} sm={6}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: 2,
                            bgcolor: "background.default",
                            borderRadius: 2,
                          }}
                        >
                          <Typography variant="subtitle2" gutterBottom>
                            Monthly Payment
                          </Typography>
                          <Typography variant="h5" sx={{ fontWeight: 600 }}>
                            ${result.monthly_payment.toFixed(2)}
                          </Typography>

                          <Divider sx={{ my: 1.5 }} />

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              Loan Amount:
                            </Typography>
                            <Typography variant="body2">
                              ${amount.toLocaleString()}
                            </Typography>
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              Interest Rate:
                            </Typography>
                            <Typography variant="body2">{rate}%</Typography>
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              Loan Term:
                            </Typography>
                            <Typography variant="body2">
                              {term} months
                            </Typography>
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                              mb: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              Total Payment:
                            </Typography>
                            <Typography variant="body2" fontWeight={500}>
                              ${(result.monthly_payment * term).toFixed(2)}
                            </Typography>
                          </Box>

                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              Total Interest:
                            </Typography>
                            <Typography variant="body2" fontWeight={500}>
                              $
                              {(result.monthly_payment * term - amount).toFixed(
                                2,
                              )}
                            </Typography>
                          </Box>
                        </Paper>
                      </Grid>
                    </Grid>

                    <Box sx={{ mt: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Payment Breakdown (First Year)
                      </Typography>
                      <Box sx={{ height: 200 }}>
                        <Line
                          data={chartData}
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                              y: {
                                beginAtZero: true,
                                title: {
                                  display: true,
                                  text: "Amount ($)",
                                },
                              },
                            },
                          }}
                        />
                      </Box>
                    </Box>

                    <Box
                      sx={{
                        mt: 3,
                        display: "flex",
                        justifyContent: "center",
                      }}
                    >
                      <Button variant="outlined" color="primary" sx={{ mr: 2 }}>
                        Save Results
                      </Button>
                      <Button variant="contained" color="secondary">
                        Apply for Loan
                      </Button>
                    </Box>
                  </Box>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>
    </motion.div>
  );
};

export default LoanCalculator;
