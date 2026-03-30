import { useNavigation } from "@react-navigation/native"; // Import useNavigation
import { Icon } from "@rneui/themed";
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  responsiveFontSize,
  responsiveHeight,
  responsiveWidth,
} from "../utils/responsive";

// Define modern color palette
const colors = {
  primary: "#4A90E2", // Modern Blue
  accent: "#50E3C2", // Teal/Mint Green
  secondaryAccent: "#F5A623", // Orange
  background: "#F8F9FA", // Light Gray
  cardBackground: "#FFFFFF", // White
  textPrimary: "#333333", // Dark Gray
  textSecondary: "#777777", // Medium Gray
  border: "#EAEAEA", // Light Gray
  success: "#50E3C2", // Using accent for success
  info: "#4A90E2", // Using primary for info
  warning: "#F5A623", // Using secondary accent for warning
  error: "#D0021B", // Red for negative changes
};

const DashboardScreen = () => {
  const navigation = useNavigation(); // Get navigation object

  // Sample score - replace with dynamic data later
  const userScore = 750;
  const scorePercentage = (userScore / 1000) * 100; // Assuming max score is 1000
  let scoreDescription = "Good";
  let scoreColor = colors.info;

  if (userScore >= 800) {
    scoreDescription = "Excellent";
    scoreColor = colors.success;
  } else if (userScore >= 700) {
    scoreDescription = "Good";
    scoreColor = colors.success; // Still positive
  } else if (userScore >= 600) {
    scoreDescription = "Fair";
    scoreColor = colors.warning;
  } else {
    scoreDescription = "Needs Improvement";
    scoreColor = colors.warning; // Or a dedicated error color
  }

  // Sample Score Factors Data
  const scoreFactors = [
    {
      name: "Payment History",
      impact: "High",
      status: "Excellent",
      icon: "check-circle",
      color: colors.success,
    },
    {
      name: "Credit Utilization",
      impact: "High",
      status: "Good",
      icon: "trending-up",
      color: colors.success,
    },
    {
      name: "Length of Credit History",
      impact: "Medium",
      status: "Good",
      icon: "history",
      color: colors.success,
    },
    {
      name: "Credit Mix",
      impact: "Low",
      status: "Fair",
      icon: "mix",
      color: colors.warning,
    }, // Custom icon name, might need adjustment
    {
      name: "New Credit",
      impact: "Low",
      status: "Good",
      icon: "fiber-new",
      color: colors.success,
    },
  ];

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Credit Dashboard</Text>
      </View>

      {/* Score Display */}
      <View style={styles.scoreContainer}>
        <Text style={styles.scoreLabel}>Your BlockScore</Text>
        <Text style={[styles.scoreValue, { color: scoreColor }]}>
          {userScore}
        </Text>
        <View style={styles.scoreBar}>
          <View
            style={[
              styles.scoreProgress,
              { width: `${scorePercentage}%`, backgroundColor: scoreColor },
            ]}
          />
        </View>
        <Text style={[styles.scoreDescription, { color: scoreColor }]}>
          {scoreDescription}
        </Text>
      </View>

      {/* Key Stats */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Icon
            name="trending-up"
            type="material"
            color={colors.success}
            size={responsiveFontSize(3.5)}
          />
          <Text style={styles.statTitle}>Credit Growth</Text>
          <Text style={styles.statValue}>+15%</Text>
        </View>
        <View style={styles.statCard}>
          <Icon
            name="history"
            type="material"
            color={colors.info}
            size={responsiveFontSize(3.5)}
          />
          <Text style={styles.statTitle}>History Length</Text>
          <Text style={styles.statValue}>5 years</Text>
        </View>
        <View style={styles.statCard}>
          <Icon
            name="account-balance"
            type="material"
            color={colors.warning}
            size={responsiveFontSize(3.5)}
          />
          <Text style={styles.statTitle}>Active Loans</Text>
          <Text style={styles.statValue}>2</Text>
        </View>
      </View>

      {/* Score Factors Section */}
      <View style={styles.factorsContainer}>
        <Text style={styles.sectionTitle}>Score Factors</Text>
        {scoreFactors.map((factor, index) => (
          <View key={index} style={styles.factorItem}>
            <Icon
              name={factor.icon}
              type="material"
              color={factor.color}
              size={responsiveFontSize(3)}
              style={styles.factorIcon}
            />
            <View style={styles.factorTextContainer}>
              <Text style={styles.factorName}>{factor.name}</Text>
              <Text style={styles.factorImpact}>Impact: {factor.impact}</Text>
            </View>
            <Text style={[styles.factorStatus, { color: factor.color }]}>
              {factor.status}
            </Text>
          </View>
        ))}
      </View>

      {/* Action Buttons */}
      <View style={styles.actionsContainer}>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("LoanCalculator")} // Navigate to Loan Calculator
        >
          <Icon
            name="calculate"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.5)}
            style={styles.buttonIcon}
          />
          <Text style={styles.actionButtonText}>Calculate Loan</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("CreditHistory")} // Navigate to Credit History
        >
          <Icon
            name="timeline"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.5)}
            style={styles.buttonIcon}
          />
          <Text style={styles.actionButtonText}>View History</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    paddingVertical: responsiveHeight(3),
    paddingHorizontal: responsiveWidth(5),
    backgroundColor: colors.primary,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  headerTitle: {
    fontSize: responsiveFontSize(3),
    fontWeight: "bold",
    color: colors.cardBackground,
    textAlign: "center",
  },
  scoreContainer: {
    alignItems: "center",
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginTop: responsiveHeight(3),
    marginBottom: responsiveHeight(2),
    padding: responsiveHeight(3),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  scoreLabel: {
    fontSize: responsiveFontSize(2.2),
    color: colors.textSecondary,
    marginBottom: responsiveHeight(0.5),
  },
  scoreValue: {
    fontSize: responsiveFontSize(6),
    fontWeight: "bold",
    marginVertical: responsiveHeight(1),
  },
  scoreBar: {
    width: "90%",
    height: responsiveHeight(1.2),
    backgroundColor: colors.border,
    borderRadius: 10,
    marginVertical: responsiveHeight(1.5),
    overflow: "hidden",
  },
  scoreProgress: {
    height: "100%",
    borderRadius: 10,
  },
  scoreDescription: {
    fontSize: responsiveFontSize(2),
    fontWeight: "600",
    marginTop: responsiveHeight(0.5),
  },
  statsContainer: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(3),
  },
  statCard: {
    backgroundColor: colors.cardBackground,
    paddingVertical: responsiveHeight(2),
    paddingHorizontal: responsiveWidth(3),
    borderRadius: 12,
    alignItems: "center",
    width: responsiveWidth(28),
    elevation: 3,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
  },
  statTitle: {
    fontSize: responsiveFontSize(1.6),
    color: colors.textSecondary,
    marginTop: responsiveHeight(1),
    textAlign: "center",
  },
  statValue: {
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
    color: colors.textPrimary,
    marginTop: responsiveHeight(0.5),
  },
  // Score Factors Styles
  factorsContainer: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(3),
    paddingHorizontal: responsiveWidth(4),
    paddingVertical: responsiveHeight(2),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: responsiveFontSize(2.2),
    fontWeight: "bold",
    color: colors.textPrimary,
    marginBottom: responsiveHeight(2),
  },
  factorItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: responsiveHeight(1.5),
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  factorItemLast: {
    borderBottomWidth: 0,
  },
  factorIcon: {
    marginRight: responsiveWidth(3),
  },
  factorTextContainer: {
    flex: 1,
  },
  factorName: {
    fontSize: responsiveFontSize(1.9),
    color: colors.textPrimary,
    fontWeight: "600",
  },
  factorImpact: {
    fontSize: responsiveFontSize(1.5),
    color: colors.textSecondary,
  },
  factorStatus: {
    fontSize: responsiveFontSize(1.8),
    fontWeight: "bold",
    marginLeft: responsiveWidth(2),
  },
  // Action Buttons Styles
  actionsContainer: {
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(4),
  },
  actionButton: {
    flexDirection: "row", // Align icon and text
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.primary,
    paddingVertical: responsiveHeight(1.8),
    borderRadius: 10,
    marginBottom: responsiveHeight(1.5),
    elevation: 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  buttonIcon: {
    marginRight: responsiveWidth(2),
  },
  actionButtonText: {
    color: colors.cardBackground,
    fontSize: responsiveFontSize(2.2),
    fontWeight: "bold",
  },
});

export default DashboardScreen;
