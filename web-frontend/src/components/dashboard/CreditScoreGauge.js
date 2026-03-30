import { Box, CircularProgress, Typography } from "@mui/material";

const CreditScoreGauge = ({ score }) => {
  // Calculate percentage for the progress circle (score range is 300-850)
  const normalizedScore = ((score - 300) / (850 - 300)) * 100;

  // Determine color based on score
  const getColor = (score) => {
    if (score >= 750) return "#4caf50"; // Green - Excellent
    if (score >= 700) return "#3f51b5"; // Blue - Good
    if (score >= 650) return "#ff9800"; // Orange - Fair
    if (score >= 600) return "#ff5722"; // Deep Orange - Poor
    return "#f44336"; // Red - Very Poor
  };

  return (
    <Box
      sx={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <CircularProgress
        variant="determinate"
        value={100}
        size={200}
        thickness={4}
        sx={{ color: (theme) => theme.palette.grey[200], position: "absolute" }}
      />
      <CircularProgress
        variant="determinate"
        value={normalizedScore}
        size={200}
        thickness={4}
        sx={{ color: getColor(score), position: "absolute" }}
      />
      <Box
        sx={{
          top: 0,
          left: 0,
          bottom: 0,
          right: 0,
          position: "absolute",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
        }}
      >
        <Typography
          variant="h3"
          component="div"
          fontWeight={700}
          color={getColor(score)}
        >
          {score}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          out of 850
        </Typography>
      </Box>
    </Box>
  );
};

export default CreditScoreGauge;
