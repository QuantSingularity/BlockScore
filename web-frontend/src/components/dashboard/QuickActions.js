// Icons
import CalculateIcon from "@mui/icons-material/Calculate";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import HistoryIcon from "@mui/icons-material/History";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Grid,
  Typography,
  useTheme,
} from "@mui/material";
import { useNavigate } from "react-router-dom";

const QuickActions = () => {
  const theme = useTheme();
  const navigate = useNavigate();

  const actions = [
    {
      title: "Calculate Loan",
      description: "Check loan eligibility",
      icon: (
        <CalculateIcon
          sx={{ fontSize: 32, color: theme.palette.primary.main }}
        />
      ),
      action: () => navigate("/loan-calculator"),
    },
    {
      title: "View History",
      description: "See transaction details",
      icon: (
        <HistoryIcon sx={{ fontSize: 32, color: theme.palette.primary.main }} />
      ),
      action: () => navigate("/history"),
    },
    {
      title: "Improve Score",
      description: "Get improvement tips",
      icon: (
        <TrendingUpIcon
          sx={{ fontSize: 32, color: theme.palette.primary.main }}
        />
      ),
      action: () => navigate("/profile"),
    },
    {
      title: "Get Help",
      description: "Support and resources",
      icon: (
        <HelpOutlineIcon
          sx={{ fontSize: 32, color: theme.palette.primary.main }}
        />
      ),
      action: () => navigate("/help"),
    },
  ];

  return (
    <Grid container spacing={2}>
      {actions.map((action, index) => (
        <Grid item xs={6} key={index}>
          <Card
            sx={{
              height: "100%",
              transition: "transform 0.2s, box-shadow 0.2s",
              "&:hover": {
                transform: "translateY(-4px)",
                boxShadow: "0 4px 10px rgba(0,0,0,0.1)",
              },
            }}
          >
            <CardActionArea
              sx={{ height: "100%", p: 1 }}
              onClick={action.action}
            >
              <CardContent sx={{ textAlign: "center" }}>
                <Box sx={{ mb: 1 }}>{action.icon}</Box>
                <Typography variant="subtitle2" fontWeight={500}>
                  {action.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {action.description}
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default QuickActions;
