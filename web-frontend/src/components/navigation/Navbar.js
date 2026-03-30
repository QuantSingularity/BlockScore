import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import MenuIcon from "@mui/icons-material/Menu";
import NotificationsIcon from "@mui/icons-material/Notifications";
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  IconButton,
  Toolbar,
  Typography,
  useTheme,
} from "@mui/material";
import { useNavigate } from "react-router-dom";

const Navbar = ({ onDrawerToggle }) => {
  const theme = useTheme();
  const navigate = useNavigate();

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: theme.zIndex.drawer + 1,
        background: "linear-gradient(90deg, #3f51b5 0%, #5c6bc0 100%)",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.1)",
      }}
    >
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onDrawerToggle}
          sx={{ mr: 2, display: { sm: "none" } }}
        >
          <MenuIcon />
        </IconButton>

        <Typography
          variant="h6"
          component="div"
          sx={{
            flexGrow: 1,
            fontFamily: '"Poppins", sans-serif',
            fontWeight: 600,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
          }}
          onClick={() => navigate("/dashboard")}
        >
          <Box
            component="span"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              borderRadius: "50%",
              backgroundColor: "white",
              color: "primary.main",
              mr: 1,
              fontWeight: 700,
              fontSize: "1.2rem",
            }}
          >
            B
          </Box>
          BlockScore
        </Typography>

        <Box sx={{ display: "flex" }}>
          <IconButton color="inherit" sx={{ ml: 1 }}>
            <Badge badgeContent={3} color="secondary">
              <NotificationsIcon />
            </Badge>
          </IconButton>

          <IconButton
            color="inherit"
            sx={{ ml: 1 }}
            onClick={() => navigate("/profile")}
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: "secondary.main" }}>
              <AccountCircleIcon />
            </Avatar>
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
