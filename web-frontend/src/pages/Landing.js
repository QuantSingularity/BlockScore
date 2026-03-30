import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import SecurityIcon from "@mui/icons-material/Security";
import SpeedIcon from "@mui/icons-material/Speed";
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Grid,
  Typography,
  useTheme,
} from "@mui/material";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

const Landing = () => {
  const theme = useTheme();
  const navigate = useNavigate();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { duration: 0.5 },
    },
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        overflow: "hidden",
      }}
    >
      {/* Hero Section */}
      <Box
        sx={{
          background: "linear-gradient(135deg, #3f51b5 0%, #5c6bc0 100%)",
          pt: { xs: 10, md: 15 },
          pb: { xs: 12, md: 18 },
          color: "white",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background decoration */}
        <Box
          sx={{
            position: "absolute",
            top: -100,
            right: -100,
            width: 400,
            height: 400,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.1)",
            zIndex: 0,
          }}
        />
        <Box
          sx={{
            position: "absolute",
            bottom: -150,
            left: -150,
            width: 300,
            height: 300,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.05)",
            zIndex: 0,
          }}
        />

        <Container maxWidth="lg" sx={{ position: "relative", zIndex: 1 }}>
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            <Grid container spacing={4} alignItems="center">
              <Grid item xs={12} md={6}>
                <motion.div variants={itemVariants}>
                  <Typography
                    variant="h2"
                    component="h1"
                    sx={{
                      fontWeight: 700,
                      mb: 2,
                      fontFamily: '"Poppins", sans-serif',
                    }}
                  >
                    Decentralized Credit Scoring
                  </Typography>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Typography
                    variant="h5"
                    sx={{
                      mb: 4,
                      fontWeight: 300,
                      opacity: 0.9,
                    }}
                  >
                    Transparent, secure, and fair credit scoring powered by
                    blockchain technology
                  </Typography>
                </motion.div>

                <motion.div variants={itemVariants}>
                  <Button
                    variant="contained"
                    size="large"
                    color="secondary"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate("/dashboard")}
                    sx={{
                      py: 1.5,
                      px: 4,
                      borderRadius: 2,
                      boxShadow: "0 8px 16px rgba(245, 0, 87, 0.24)",
                    }}
                  >
                    Get Started
                  </Button>
                </motion.div>
              </Grid>

              <Grid item xs={12} md={6}>
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.8, delay: 0.3 }}
                >
                  <Box
                    component="img"
                    src="/hero-image.svg"
                    alt="BlockScore Hero"
                    sx={{
                      width: "100%",
                      maxWidth: 500,
                      display: "block",
                      mx: "auto",
                    }}
                  />
                </motion.div>
              </Grid>
            </Grid>
          </motion.div>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Typography
            variant="h3"
            component="h2"
            align="center"
            sx={{
              mb: 6,
              fontFamily: '"Poppins", sans-serif',
              fontWeight: 600,
            }}
          >
            Why Choose BlockScore
          </Typography>
        </motion.div>

        <Grid container spacing={4}>
          {[
            {
              icon: (
                <SecurityIcon
                  sx={{ fontSize: 50, color: theme.palette.primary.main }}
                />
              ),
              title: "Secure & Transparent",
              description:
                "All credit data is securely stored on the blockchain, ensuring transparency and immutability.",
            },
            {
              icon: (
                <SpeedIcon
                  sx={{ fontSize: 50, color: theme.palette.primary.main }}
                />
              ),
              title: "Real-time Updates",
              description:
                "Credit scores are updated in real-time as new transactions are recorded on the blockchain.",
            },
            {
              icon: (
                <AccountBalanceIcon
                  sx={{ fontSize: 50, color: theme.palette.primary.main }}
                />
              ),
              title: "Fair Lending",
              description:
                "AI-powered scoring models ensure fair and unbiased credit assessment for all users.",
            },
          ].map((feature, index) => (
            <Grid item xs={12} md={4} key={index}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.3 + index * 0.2 }}
              >
                <Card
                  className="card-hover-effect"
                  sx={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    p: 3,
                    textAlign: "center",
                  }}
                >
                  <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Typography
                      gutterBottom
                      variant="h5"
                      component="h3"
                      sx={{
                        fontWeight: 600,
                        mb: 2,
                      }}
                    >
                      {feature.title}
                    </Typography>
                    <Typography variant="body1" color="text.secondary">
                      {feature.description}
                    </Typography>
                  </CardContent>
                </Card>
              </motion.div>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA Section */}
      <Box
        sx={{
          bgcolor: "primary.light",
          py: 8,
          mt: 8,
        }}
      >
        <Container maxWidth="md">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Card
              sx={{
                p: 4,
                borderRadius: 4,
                boxShadow: "0 10px 30px rgba(0, 0, 0, 0.1)",
                background: "linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)",
              }}
            >
              <CardContent sx={{ textAlign: "center" }}>
                <Typography
                  variant="h4"
                  component="h3"
                  sx={{
                    mb: 2,
                    fontWeight: 600,
                    fontFamily: '"Poppins", sans-serif',
                  }}
                >
                  Ready to Get Started?
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  sx={{ mb: 4, maxWidth: 600, mx: "auto" }}
                >
                  Join thousands of users who are already benefiting from our
                  decentralized credit scoring system. Check your score, apply
                  for loans, and take control of your financial future.
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => navigate("/dashboard")}
                  sx={{
                    py: 1.5,
                    px: 4,
                    borderRadius: 2,
                  }}
                >
                  Check Your Score Now
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </Container>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          bgcolor: "background.paper",
          py: 6,
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        <Container maxWidth="lg">
          <Typography variant="body2" color="text.secondary" align="center">
            © {new Date().getFullYear()} BlockScore | All rights reserved
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            align="center"
            sx={{ mt: 1 }}
          >
            Powered by blockchain technology for secure and transparent credit
            scoring
          </Typography>
        </Container>
      </Box>
    </Box>
  );
};

export default Landing;
