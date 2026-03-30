import { Box, Link, Typography } from "@mui/material";

const Footer = () => {
  return (
    <Box
      component="footer"
      sx={{
        py: 3,
        mt: "auto",
        textAlign: "center",
        borderTop: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography variant="body2" color="text.secondary">
        © {new Date().getFullYear()} BlockScore | All rights reserved
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        <Link href="#" color="inherit" sx={{ mx: 1 }}>
          Privacy Policy
        </Link>
        <Link href="#" color="inherit" sx={{ mx: 1 }}>
          Terms of Service
        </Link>
        <Link href="#" color="inherit" sx={{ mx: 1 }}>
          Contact
        </Link>
      </Typography>
    </Box>
  );
};

export default Footer;
