import {
  Box,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Typography,
  useTheme,
} from "@mui/material";
import { format } from "date-fns";
import React from "react";

const TransactionHistory = ({ history }) => {
  const _theme = useTheme();

  // Sort history by timestamp (newest first)
  const sortedHistory = [...history].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <Box>
      {history.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
          No transaction history available
        </Typography>
      ) : (
        <List disablePadding>
          {sortedHistory.map((transaction, index) => (
            <React.Fragment key={index}>
              {index > 0 && <Divider component="li" />}
              <ListItem
                alignItems="flex-start"
                sx={{
                  py: 2,
                  transition: "background-color 0.3s",
                  "&:hover": {
                    backgroundColor: "rgba(0, 0, 0, 0.02)",
                  },
                }}
              >
                <ListItemText
                  primary={
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="subtitle1" fontWeight={500}>
                        ${transaction.amount.toLocaleString()}
                      </Typography>
                      <Chip
                        label={transaction.repaid ? "Repaid" : "Outstanding"}
                        color={transaction.repaid ? "success" : "warning"}
                        size="small"
                      />
                    </Box>
                  }
                  secondary={
                    <React.Fragment>
                      <Typography
                        component="span"
                        variant="body2"
                        color="text.primary"
                      >
                        Transaction ID:{" "}
                        {`TX${Math.floor(Math.random() * 1000000)
                          .toString()
                          .padStart(6, "0")}`}
                      </Typography>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.5 }}
                      >
                        {format(new Date(transaction.timestamp), "PPP")}
                      </Typography>
                    </React.Fragment>
                  }
                />
              </ListItem>
            </React.Fragment>
          ))}
        </List>
      )}
    </Box>
  );
};

export default TransactionHistory;
