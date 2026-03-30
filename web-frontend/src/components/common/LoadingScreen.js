import { Box, CircularProgress, Typography } from "@mui/material";
import { motion } from "framer-motion";

const LoadingScreen = () => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        bgcolor: "background.default",
      }}
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <CircularProgress size={60} thickness={4} />
      </motion.div>

      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <Typography
          variant="h5"
          sx={{
            mt: 3,
            fontFamily: '"Poppins", sans-serif',
            fontWeight: 500,
          }}
        >
          Loading BlockScore
        </Typography>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
      >
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Decentralized Credit Scoring System
        </Typography>
      </motion.div>
    </Box>
  );
};

export default LoadingScreen;
