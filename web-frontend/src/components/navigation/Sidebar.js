import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import CalculateIcon from "@mui/icons-material/Calculate";
// Icons
import DashboardIcon from "@mui/icons-material/Dashboard";
import HelpIcon from "@mui/icons-material/Help";
import HistoryIcon from "@mui/icons-material/History";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  Box,
  Divider,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const drawerWidth = 240;

const Sidebar = ({ mobileOpen, onDrawerToggle }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const _isDesktop = useMediaQuery(theme.breakpoints.up("sm"));

  const [open, setOpen] = useState({
    transactions: false,
    settings: false,
  });

  const _handleClick = (section) => {
    setOpen({
      ...open,
      [section]: !open[section],
    });
  };

  const menuItems = [
    {
      text: "Dashboard",
      icon: <DashboardIcon />,
      path: "/dashboard",
    },
    {
      text: "Loan Calculator",
      icon: <CalculateIcon />,
      path: "/loan-calculator",
    },
    {
      text: "Wallet",
      icon: <AccountBalanceWalletIcon />,
      path: "/profile",
    },
    {
      text: "Transaction History",
      icon: <HistoryIcon />,
      path: "/history",
    },
    {
      text: "Settings",
      icon: <SettingsIcon />,
      path: "/settings",
    },
    {
      text: "Help & Support",
      icon: <HelpIcon />,
      path: "/help",
    },
  ];

  const drawer = (
    <div>
      <Box
        sx={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Typography
          variant="h6"
          sx={{
            fontFamily: '"Poppins", sans-serif',
            fontWeight: 600,
            color: theme.palette.primary.main,
          }}
        >
          BlockScore
        </Typography>
      </Box>
      <List sx={{ pt: 2 }}>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => navigate(item.path)}
            sx={{
              mb: 0.5,
              py: 1,
              borderRadius: "8px",
              mx: 1,
              "&:hover": {
                backgroundColor: "rgba(63, 81, 181, 0.08)",
              },
              ...(location.pathname === item.path && {
                backgroundColor: "rgba(63, 81, 181, 0.12)",
                "&:hover": {
                  backgroundColor: "rgba(63, 81, 181, 0.16)",
                },
                "&::before": {
                  content: '""',
                  position: "absolute",
                  left: 0,
                  top: "25%",
                  height: "50%",
                  width: 4,
                  backgroundColor: theme.palette.primary.main,
                  borderRadius: "0 4px 4px 0",
                },
              }),
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: 40,
                color:
                  location.pathname === item.path
                    ? theme.palette.primary.main
                    : theme.palette.text.secondary,
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.text}
              primaryTypographyProps={{
                fontWeight: location.pathname === item.path ? 500 : 400,
                color:
                  location.pathname === item.path
                    ? theme.palette.primary.main
                    : theme.palette.text.primary,
              }}
            />
          </ListItem>
        ))}
      </List>
      <Divider sx={{ my: 2 }} />
      <Box sx={{ p: 2 }}>
        <Typography variant="body2" color="text.secondary" align="center">
          BlockScore v1.0.0
        </Typography>
      </Box>
    </div>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
    >
      {/* Mobile drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: "block", sm: "none" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: drawerWidth,
            boxShadow: "0 10px 30px rgba(0, 0, 0, 0.1)",
          },
        }}
      >
        {drawer}
      </Drawer>

      {/* Desktop drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", sm: "block" },
          "& .MuiDrawer-paper": {
            boxSizing: "border-box",
            width: drawerWidth,
            borderRight: `1px solid ${theme.palette.divider}`,
            boxShadow: "none",
          },
        }}
        open
      >
        {drawer}
      </Drawer>
    </Box>
  );
};

export default Sidebar;
