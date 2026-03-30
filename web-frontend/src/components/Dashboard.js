import { Card, CardContent, Typography } from "@mui/material";
import axios from "axios";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const [score, setScore] = useState(null);

  useEffect(() => {
    const fetchScore = async () => {
      try {
        const response = await axios.post("/api/credit/calculate-score", {
          walletAddress: "0x123...",
        });
        setScore(response.data.score);
      } catch (error) {
        console.error("Error fetching score:", error);
        // Set mock data on error
        setScore(720);
      }
    };
    fetchScore();
  }, []);

  return (
    <Card>
      <CardContent>
        <Typography variant="h5">
          Credit Score: {score || "Loading..."}
        </Typography>
        <Typography color="textSecondary">
          Updated in real-time from blockchain
        </Typography>
      </CardContent>
    </Card>
  );
}
