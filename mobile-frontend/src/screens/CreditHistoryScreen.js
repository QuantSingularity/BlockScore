import { useNavigation } from "@react-navigation/native"; // Import useNavigation
import { Icon } from "@rneui/themed";
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native"; // Import Alert
import { LineChart } from "react-native-chart-kit";
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
  error: "#D0021B", // Red for negative changes
};

const CreditHistoryScreen = () => {
  const navigation = useNavigation(); // Get navigation object

  // Sample data for the chart
  const data = {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
    datasets: [
      {
        data: [680, 700, 710, 695, 730, 750],
        color: (opacity = 1) => `rgba(74, 144, 226, ${opacity})`, // Use primary color
        strokeWidth: 3,
      },
    ],
    legend: ["Credit Score Trend"],
  };

  const chartConfig = {
    backgroundGradientFrom: colors.cardBackground,
    backgroundGradientTo: colors.cardBackground,
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(74, 144, 226, ${opacity})`, // Primary color for lines/labels
    labelColor: (opacity = 1) => `rgba(51, 51, 51, ${opacity})`, // textPrimary for labels
    style: {
      borderRadius: 15,
    },
    propsForDots: {
      r: "5",
      strokeWidth: "2",
      stroke: colors.primary,
    },
    propsForBackgroundLines: {
      strokeDasharray: "", // Solid lines
      stroke: colors.border, // Use border color for grid lines
    },
  };

  // Sample history data
  const historyData = [
    {
      date: "APR 15",
      title: "Loan Payment",
      description: "On-time payment recorded",
      scoreChange: 5,
    },
    {
      date: "MAR 22",
      title: "Credit Inquiry",
      description: "Mortgage pre-approval",
      scoreChange: -2,
    },
    {
      date: "MAR 10",
      title: "Credit Card Payment",
      description: "Paid in full",
      scoreChange: 3,
    },
    {
      date: "FEB 28",
      title: "Loan Payment",
      description: "On-time payment recorded",
      scoreChange: 5,
    },
    {
      date: "JAN 15",
      title: "New Credit Card",
      description: "Account opened",
      scoreChange: -1,
    },
  ];

  // Placeholder action for View Full History button
  const handleViewFullHistory = () => {
    Alert.alert(
      "View Full History",
      "This feature is not yet implemented. Accessing full history requires backend integration.",
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
        <Text style={styles.headerTitle}>Credit History</Text>
        <View style={styles.headerPlaceholder} />
        {/* To balance the back button */}
      </View>

      <View style={styles.chartContainer}>
        <Text style={styles.sectionTitle}>Score Trend</Text>
        <LineChart
          data={data}
          width={responsiveWidth(90)} // Adjust width slightly for padding
          height={responsiveHeight(30)}
          chartConfig={chartConfig}
          bezier // Smooth curve
          style={styles.chart}
        />
      </View>

      <View style={styles.historyContainer}>
        <Text style={styles.sectionTitle}>Recent Activities</Text>

        {historyData.map((item, index) => (
          <View
            key={index}
            style={[
              styles.historyItem,
              index === historyData.length - 1 ? styles.historyItemLast : null,
            ]}
          >
            <View style={styles.historyDate}>
              <Text style={styles.dateText}>{item.date.split(" ")[0]}</Text>
              <Text style={styles.dateNumber}>{item.date.split(" ")[1]}</Text>
            </View>
            <View style={styles.historyContent}>
              <Text style={styles.historyTitle}>{item.title}</Text>
              <Text style={styles.historyDescription}>{item.description}</Text>
            </View>
            <View style={styles.historyScore}>
              <Text
                style={[
                  styles.scoreChange,
                  item.scoreChange < 0 ? styles.negative : styles.positive,
                ]}
              >
                {item.scoreChange > 0
                  ? `+${item.scoreChange}`
                  : item.scoreChange}
              </Text>
            </View>
          </View>
        ))}
      </View>

      <TouchableOpacity
        style={styles.actionButton}
        onPress={handleViewFullHistory}
      >
        <Icon
          name="description"
          type="material"
          color={colors.cardBackground}
          size={responsiveFontSize(2.5)}
          style={styles.buttonIcon}
        />
        <Text style={styles.actionButtonText}>View Full History</Text>
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
  chartContainer: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginTop: responsiveHeight(3),
    marginBottom: responsiveHeight(2),
    padding: responsiveHeight(2),
    borderRadius: 15,
    alignItems: "center",
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
    alignSelf: "flex-start",
    marginLeft: responsiveWidth(2),
  },
  chart: {
    marginVertical: responsiveHeight(1),
    borderRadius: 15,
  },
  historyContainer: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(2),
    paddingVertical: responsiveHeight(1),
    paddingHorizontal: responsiveWidth(3),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  historyItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: responsiveHeight(1.8),
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  historyItemLast: {
    borderBottomWidth: 0,
  },
  historyDate: {
    width: responsiveWidth(13),
    alignItems: "center",
    justifyContent: "center",
    marginRight: responsiveWidth(3),
    paddingVertical: responsiveHeight(0.5),
    backgroundColor: colors.background,
    borderRadius: 8,
  },
  dateText: {
    fontSize: responsiveFontSize(1.5),
    color: colors.textSecondary,
    fontWeight: "bold",
    textTransform: "uppercase",
  },
  dateNumber: {
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
    color: colors.textPrimary,
  },
  historyContent: {
    flex: 1,
  },
  historyTitle: {
    fontSize: responsiveFontSize(1.9),
    fontWeight: "600",
    color: colors.textPrimary,
    marginBottom: responsiveHeight(0.3),
  },
  historyDescription: {
    fontSize: responsiveFontSize(1.6),
    color: colors.textSecondary,
  },
  historyScore: {
    width: responsiveWidth(12),
    alignItems: "flex-end",
    justifyContent: "center",
  },
  scoreChange: {
    fontSize: responsiveFontSize(1.9),
    fontWeight: "bold",
  },
  positive: {
    color: colors.success,
  },
  negative: {
    color: colors.error,
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

export default CreditHistoryScreen;
