import { Box, Button, Container, Typography } from "@mui/material";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <Container maxWidth="md">
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "80vh",
          textAlign: "center",
          py: 8,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Typography
            variant="h1"
            component="h1"
            sx={{
              fontSize: { xs: "6rem", md: "10rem" },
              fontWeight: 700,
              background: "linear-gradient(45deg, #3f51b5 30%, #f50057 90%)",
              backgroundClip: "text",
              textFillColor: "transparent",
              mb: 2,
            }}
          >
            404
          </Typography>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Typography
            variant="h4"
            component="h2"
            sx={{
              mb: 3,
              fontWeight: 600,
              fontFamily: '"Poppins", sans-serif',
            }}
          >
            Page Not Found
          </Typography>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mb: 4, maxWidth: 500 }}
          >
            The page you are looking for might have been removed, had its name
            changed, or is temporarily unavailable.
          </Typography>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate("/dashboard")}
            sx={{ mr: 2 }}
          >
            Go to Dashboard
          </Button>
          <Button variant="outlined" size="large" onClick={() => navigate("/")}>
            Back to Home
          </Button>
        </motion.div>
      </Box>
    </Container>
  );
};

export default NotFound;
