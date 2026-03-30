import { useNavigation } from "@react-navigation/native"; // Import useNavigation
import { Icon, Slider } from "@rneui/themed"; // Import Icon
import React from "react";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native"; // Import Alert
import {
  responsiveFontSize,
  responsiveHeight,
  responsiveWidth,
} from "../utils/responsive";

// Define modern color palette (same as other screens)
const colors = {
  primary: "#4A90E2", // Modern Blue
  accent: "#50E3C2", // Teal/Mint Green
  secondaryAccent: "#F5A623", // Orange
  background: "#F8F9FA", // Light Gray
  cardBackground: "#FFFFFF", // White
  textPrimary: "#333333", // Dark Gray
  textSecondary: "#777777", // Medium Gray
  border: "#EAEAEA", // Light Gray
  success: "#50E3C2",
  info: "#4A90E2",
  warning: "#F5A623",
  error: "#D0021B",
};

const LoanCalculatorScreen = () => {
  const navigation = useNavigation(); // Get navigation object
  const [loanAmount, setLoanAmount] = React.useState(10000);
  const [loanTerm, setLoanTerm] = React.useState(36);
  const [interestRate, setInterestRate] = React.useState(5.5);

  // Calculate monthly payment
  const calculateMonthlyPayment = () => {
    const principal = loanAmount;
    const monthlyRate = interestRate / 100 / 12;
    const numberOfPayments = loanTerm;

    if (principal <= 0 || monthlyRate <= 0 || numberOfPayments <= 0) {
      return "0.00";
    }

    const monthlyPayment =
      (principal * monthlyRate * (1 + monthlyRate) ** numberOfPayments) /
      ((1 + monthlyRate) ** numberOfPayments - 1);

    return Number.isNaN(monthlyPayment) || !Number.isFinite(monthlyPayment)
      ? "0.00"
      : monthlyPayment.toFixed(2);
  };

  // Calculate total payment
  const calculateTotalPayment = () => {
    const monthlyPayment = parseFloat(calculateMonthlyPayment());
    return (monthlyPayment * loanTerm).toFixed(2);
  };

  // Calculate total interest
  const calculateTotalInterest = () => {
    const totalPayment = parseFloat(calculateTotalPayment());
    return (totalPayment - loanAmount).toFixed(2);
  };

  // Format large numbers for display
  const formatNumber = (num) => {
    // Ensure num is a number before formatting
    const numberValue = parseFloat(num);
    if (Number.isNaN(numberValue)) {
      return "0";
    }
    return numberValue.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  // Placeholder action for Apply button
  const handleApplyLoan = () => {
    Alert.alert(
      "Apply for Loan",
      "This feature is not yet implemented. Loan application functionality requires backend integration.",
      [{ text: "OK" }],
    );
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <Icon
            name="arrow-back-ios"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.5)}
          />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Loan Calculator</Text>
        <View style={styles.headerPlaceholder} />
        {/* To balance the back button */}
      </View>

      <View style={styles.calculatorContainer}>
        {/* Loan Amount Input */}
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Loan Amount</Text>
          <View style={styles.inputDisplayContainer}>
            <Text style={styles.inputDisplayValue}>
              ${formatNumber(loanAmount)}
            </Text>
          </View>
          <Slider
            value={loanAmount}
            onValueChange={(value) => setLoanAmount(value)}
            minimumValue={1000}
            maximumValue={100000}
            step={1000}
            thumbStyle={styles.thumbStyle}
            trackStyle={styles.trackStyle}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.border}
          />
          <View style={styles.sliderLabels}>
            <Text style={styles.sliderLabel}>$1,000</Text>
            <Text style={styles.sliderLabel}>$100,000</Text>
          </View>
        </View>

        {/* Loan Term Input */}
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Loan Term</Text>
          <View style={styles.inputDisplayContainer}>
            <Text style={styles.inputDisplayValue}>{loanTerm} months</Text>
          </View>
          <Slider
            value={loanTerm}
            onValueChange={(value) => setLoanTerm(value)}
            minimumValue={12}
            maximumValue={84}
            step={12}
            thumbStyle={styles.thumbStyle}
            trackStyle={styles.trackStyle}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.border}
          />
          <View style={styles.sliderLabels}>
            <Text style={styles.sliderLabel}>12 mo</Text>
            <Text style={styles.sliderLabel}>84 mo</Text>
          </View>
        </View>

        {/* Interest Rate Input */}
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Interest Rate</Text>
          <View style={styles.inputDisplayContainer}>
            <Text style={styles.inputDisplayValue}>
              {interestRate.toFixed(1)}%
            </Text>
          </View>
          <Slider
            value={interestRate}
            onValueChange={(value) => setInterestRate(value)}
            minimumValue={1}
            maximumValue={20}
            step={0.1}
            thumbStyle={styles.thumbStyle}
            trackStyle={styles.trackStyle}
            minimumTrackTintColor={colors.primary}
            maximumTrackTintColor={colors.border}
          />
          <View style={styles.sliderLabels}>
            <Text style={styles.sliderLabel}>1.0%</Text>
            <Text style={styles.sliderLabel}>20.0%</Text>
          </View>
        </View>
      </View>

      {/* Results Section */}
      <View style={styles.resultsContainer}>
        <Text style={styles.resultsTitle}>Estimated Loan Summary</Text>

        <View style={styles.resultRow}>
          <Text style={styles.resultLabel}>Monthly Payment:</Text>
          <Text style={styles.resultValue}>${calculateMonthlyPayment()}</Text>
        </View>

        <View style={styles.resultRow}>
          <Text style={styles.resultLabel}>Total Principal:</Text>
          <Text style={styles.resultValue}>${formatNumber(loanAmount)}</Text>
        </View>

        <View style={styles.resultRow}>
          <Text style={styles.resultLabel}>Total Interest:</Text>
          <Text style={styles.resultValue}>
            ${formatNumber(calculateTotalInterest())}
          </Text>
        </View>

        <View style={[styles.resultRow, styles.resultRowLast]}>
          <Text style={styles.resultLabelTotal}>Total Payment:</Text>
          <Text style={styles.resultValueTotal}>
            ${formatNumber(calculateTotalPayment())}
          </Text>
        </View>
      </View>

      <TouchableOpacity style={styles.actionButton} onPress={handleApplyLoan}>
        <Icon
          name="check-circle"
          type="material"
          color={colors.cardBackground}
          size={responsiveFontSize(2.5)}
          style={styles.buttonIcon}
        />
        <Text style={styles.actionButtonText}>Apply for Loan</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: "row", // Align items horizontally
    alignItems: "center", // Center items vertically
    justifyContent: "space-between", // Space out back button, title, placeholder
    paddingVertical: responsiveHeight(2.5),
    paddingHorizontal: responsiveWidth(4),
    backgroundColor: colors.primary,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 20,
  },
  backButton: {
    padding: responsiveWidth(1),
  },
  headerTitle: {
    fontSize: responsiveFontSize(2.8),
    fontWeight: "bold",
    color: colors.cardBackground,
    textAlign: "center",
  },
  headerPlaceholder: {
    width: responsiveWidth(8), // Match approx width of back button for balance
  },
  calculatorContainer: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginTop: responsiveHeight(3),
    marginBottom: responsiveHeight(2),
    paddingHorizontal: responsiveWidth(5),
    paddingVertical: responsiveHeight(2.5),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  inputGroup: {
    marginBottom: responsiveHeight(3),
  },
  inputLabel: {
    fontSize: responsiveFontSize(1.8),
    color: colors.textSecondary,
    marginBottom: responsiveHeight(1.5),
    fontWeight: "600",
  },
  inputDisplayContainer: {
    backgroundColor: colors.background,
    paddingVertical: responsiveHeight(1.5),
    paddingHorizontal: responsiveWidth(4),
    borderRadius: 8,
    marginBottom: responsiveHeight(1.5),
    alignItems: "center",
  },
  inputDisplayValue: {
    fontSize: responsiveFontSize(2.2),
    color: colors.textPrimary,
    fontWeight: "bold",
  },
  thumbStyle: {
    height: responsiveHeight(3),
    width: responsiveHeight(3),
    backgroundColor: colors.primary,
    borderRadius: responsiveHeight(1.5),
  },
  trackStyle: {
    height: responsiveHeight(1),
    borderRadius: 5,
  },
  sliderLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: responsiveHeight(0.5),
  },
  sliderLabel: {
    fontSize: responsiveFontSize(1.5),
    color: colors.textSecondary,
  },
  resultsContainer: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(2),
    paddingHorizontal: responsiveWidth(5),
    paddingVertical: responsiveHeight(2),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  resultsTitle: {
    fontSize: responsiveFontSize(2.2),
    fontWeight: "bold",
    color: colors.textPrimary,
    marginBottom: responsiveHeight(2.5),
    textAlign: "center",
  },
  resultRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: responsiveHeight(1.5),
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  resultRowLast: {
    borderBottomWidth: 0,
    paddingTop: responsiveHeight(2),
    marginTop: responsiveHeight(1),
  },
  resultLabel: {
    fontSize: responsiveFontSize(1.8),
    color: colors.textSecondary,
  },
  resultValue: {
    fontSize: responsiveFontSize(1.8),
    fontWeight: "600",
    color: colors.textPrimary,
  },
  resultLabelTotal: {
    fontSize: responsiveFontSize(2),
    color: colors.textPrimary,
    fontWeight: "bold",
  },
  resultValueTotal: {
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
    color: colors.primary,
  },
  actionButton: {
    flexDirection: "row", // Align icon and text
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.primary,
    paddingVertical: responsiveHeight(1.8),
    borderRadius: 10,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(4),
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

export default LoanCalculatorScreen;
