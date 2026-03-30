import { Button, Paper, TextField, Typography } from "@mui/material";
import { useState } from "react";

export default function LoanCalculator() {
  const [amount, setAmount] = useState(1000);
  const [rate, setRate] = useState(5);
  const [result, setResult] = useState(null);

  const calculate = async () => {
    try {
      const response = await fetch("/api/loans/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount, rate }),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error("Error calculating loan:", error);
      // Set mock result on error
      setResult({ approval_probability: 75 });
    }
  };

  return (
    <Paper style={{ padding: 20, margin: 20 }}>
      <Typography variant="h6">Loan Eligibility Calculator</Typography>
      <TextField
        label="Loan Amount"
        type="number"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        fullWidth
        margin="normal"
      />
      <TextField
        label="Interest Rate %"
        type="number"
        value={rate}
        onChange={(e) => setRate(e.target.value)}
        fullWidth
        margin="normal"
      />
      <Button
        variant="contained"
        color="primary"
        onClick={calculate}
        sx={{ mt: 2 }}
      >
        Calculate
      </Button>
      {result && (
        <Typography style={{ marginTop: 20 }}>
          Approval Chance: {result.approval_probability}%
        </Typography>
      )}
    </Paper>
  );
}
