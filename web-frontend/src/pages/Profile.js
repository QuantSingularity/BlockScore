// Icons
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HistoryIcon from "@mui/icons-material/History";
import SecurityIcon from "@mui/icons-material/Security";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Typography,
  useTheme,
} from "@mui/material";
import { motion } from "framer-motion";
import { useAuth } from "../contexts/AuthContext";
import { useWeb3 } from "../contexts/Web3Context";

const Profile = () => {
  const theme = useTheme();
  const { user, logout } = useAuth();
  const { accounts, networkId } = useWeb3();

  const walletAddress =
    accounts[0] ||
    user?.address ||
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e";

  // Format wallet address for display
  const formatAddress = (address) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  // Get network name
  const getNetworkName = (id) => {
    switch (id) {
      case 1:
        return "Ethereum Mainnet";
      case 3:
        return "Ropsten Testnet";
      case 4:
        return "Rinkeby Testnet";
      case 5:
        return "Goerli Testnet";
      case 42:
        return "Kovan Testnet";
      default:
        return "Unknown Network";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
          Profile
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage your wallet and account settings.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Wallet Information */}
        <Grid item xs={12} md={4}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    mb: 3,
                  }}
                >
                  <Avatar
                    sx={{
                      width: 80,
                      height: 80,
                      bgcolor: "primary.main",
                      mb: 2,
                    }}
                  >
                    <AccountBalanceWalletIcon sx={{ fontSize: 40 }} />
                  </Avatar>

                  <Typography variant="h6" align="center" gutterBottom>
                    {user?.name || "Wallet User"}
                  </Typography>

                  <Chip
                    label={formatAddress(walletAddress)}
                    color="primary"
                    variant="outlined"
                    sx={{ fontFamily: '"Roboto Mono", monospace' }}
                  />
                </Box>

                <Divider sx={{ my: 2 }} />

                <List disablePadding>
                  <ListItem disablePadding sx={{ mb: 1 }}>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <SecurityIcon fontSize="small" color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Network"
                      secondary={getNetworkName(networkId)}
                    />
                  </ListItem>

                  <ListItem disablePadding sx={{ mb: 1 }}>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <HistoryIcon fontSize="small" color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Transactions"
                      secondary="23 completed"
                    />
                  </ListItem>

                  <ListItem disablePadding>
                    <ListItemIcon sx={{ minWidth: 40 }}>
                      <SettingsIcon fontSize="small" color="primary" />
                    </ListItemIcon>
                    <ListItemText primary="Account Type" secondary="Standard" />
                  </ListItem>
                </List>

                <Button
                  variant="outlined"
                  color="primary"
                  fullWidth
                  sx={{ mt: 3 }}
                  onClick={logout}
                >
                  Disconnect Wallet
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Credit Status */}
        <Grid item xs={12} md={8}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Credit Status
                </Typography>

                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        bgcolor: "background.default",
                        borderRadius: 2,
                        height: "100%",
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        gutterBottom
                      >
                        Credit Score
                      </Typography>
                      <Typography
                        variant="h4"
                        sx={{ fontWeight: 600, color: "primary.main" }}
                      >
                        720
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Good
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        bgcolor: "background.default",
                        borderRadius: 2,
                        height: "100%",
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        gutterBottom
                      >
                        Active Loans
                      </Typography>
                      <Typography variant="h4" sx={{ fontWeight: 600 }}>
                        1
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        $5,000 outstanding
                      </Typography>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} sm={4}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        bgcolor: "background.default",
                        borderRadius: 2,
                        height: "100%",
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        gutterBottom
                      >
                        Repayment Rate
                      </Typography>
                      <Typography
                        variant="h4"
                        sx={{ fontWeight: 600, color: "success.main" }}
                      >
                        98%
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Excellent
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>

                <Typography
                  variant="subtitle1"
                  gutterBottom
                  sx={{ mt: 4, mb: 2 }}
                >
                  Credit Factors
                </Typography>

                <List>
                  {[
                    {
                      factor: "Payment History",
                      status: "Excellent",
                      description:
                        "You have a strong history of on-time payments",
                      positive: true,
                    },
                    {
                      factor: "Credit Utilization",
                      status: "Good",
                      description:
                        "Your current loan amount is well within your capacity",
                      positive: true,
                    },
                    {
                      factor: "Credit Age",
                      status: "Fair",
                      description: "Your credit history is relatively new",
                      positive: false,
                    },
                    {
                      factor: "Credit Mix",
                      status: "Poor",
                      description: "You have limited variety in credit types",
                      positive: false,
                    },
                  ].map((item, index) => (
                    <ListItem
                      key={index}
                      sx={{
                        py: 1.5,
                        px: 2,
                        mb: 1,
                        bgcolor: "background.default",
                        borderRadius: 2,
                      }}
                    >
                      <ListItemIcon>
                        {item.positive ? (
                          <CheckCircleIcon color="success" />
                        ) : (
                          <ErrorIcon color="warning" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box
                            sx={{
                              display: "flex",
                              justifyContent: "space-between",
                            }}
                          >
                            <Typography variant="body1" fontWeight={500}>
                              {item.factor}
                            </Typography>
                            <Chip
                              label={item.status}
                              size="small"
                              color={
                                item.status === "Excellent"
                                  ? "success"
                                  : item.status === "Good"
                                    ? "primary"
                                    : item.status === "Fair"
                                      ? "warning"
                                      : "error"
                              }
                              sx={{ fontWeight: 500 }}
                            />
                          </Box>
                        }
                        secondary={item.description}
                      />
                    </ListItem>
                  ))}
                </List>

                <Box sx={{ mt: 3, display: "flex", justifyContent: "center" }}>
                  <Button variant="contained" color="primary">
                    View Detailed Report
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Improvement Tips */}
        <Grid item xs={12}>
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Credit Improvement Tips
                </Typography>

                <Grid container spacing={2} sx={{ mt: 1 }}>
                  {[
                    {
                      title: "Diversify Your Credit Mix",
                      description:
                        "Consider adding different types of credit to your portfolio, such as a small secured loan.",
                      icon: (
                        <SettingsIcon
                          sx={{
                            fontSize: 40,
                            color: theme.palette.primary.main,
                          }}
                        />
                      ),
                    },
                    {
                      title: "Build Credit History",
                      description:
                        "Continue making on-time payments to establish a longer credit history.",
                      icon: (
                        <HistoryIcon
                          sx={{
                            fontSize: 40,
                            color: theme.palette.primary.main,
                          }}
                        />
                      ),
                    },
                    {
                      title: "Monitor Your Score",
                      description:
                        "Regularly check your credit score to track improvements and detect issues early.",
                      icon: (
                        <SecurityIcon
                          sx={{
                            fontSize: 40,
                            color: theme.palette.primary.main,
                          }}
                        />
                      ),
                    },
                  ].map((tip, index) => (
                    <Grid item xs={12} md={4} key={index}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          height: "100%",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          textAlign: "center",
                          bgcolor: "background.default",
                          borderRadius: 2,
                        }}
                      >
                        <Box sx={{ mb: 2 }}>{tip.icon}</Box>
                        <Typography
                          variant="subtitle1"
                          gutterBottom
                          fontWeight={500}
                        >
                          {tip.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {tip.description}
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>
      </Grid>
    </motion.div>
  );
};

export default Profile;
