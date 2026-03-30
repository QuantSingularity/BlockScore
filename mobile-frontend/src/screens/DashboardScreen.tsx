import { useNavigation } from "@react-navigation/native";
import { Icon } from "@rneui/themed";
import React, { useEffect } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  fetchCreditScore,
  fetchScoreFactors,
} from "../store/slices/creditSlice";
import { fetchBorrowerLoans } from "../store/slices/loanSlice";
import {
  responsiveFontSize,
  responsiveHeight,
  responsiveWidth,
} from "../utils/responsive";

const colors = {
  primary: "#4A90E2",
  accent: "#50E3C2",
  secondaryAccent: "#F5A623",
  background: "#F8F9FA",
  cardBackground: "#FFFFFF",
  textPrimary: "#333333",
  textSecondary: "#777777",
  border: "#EAEAEA",
  success: "#50E3C2",
  info: "#4A90E2",
  warning: "#F5A623",
  error: "#D0021B",
};

const DashboardScreen = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const {
    score,
    scoreFactors,
    isLoading: creditLoading,
  } = useAppSelector((state) => state.credit);
  const { loans, isLoading: loansLoading } = useAppSelector(
    (state) => state.loan,
  );

  const [refreshing, setRefreshing] = React.useState(false);

  const loadData = async () => {
    if (user?.walletAddress) {
      try {
        await Promise.all([
          dispatch(fetchCreditScore(user.walletAddress)).unwrap(),
          dispatch(fetchScoreFactors(user.walletAddress)).unwrap(),
          dispatch(fetchBorrowerLoans(user.walletAddress)).unwrap(),
        ]);
      } catch (error) {
        console.error("Error loading data:", error);
      }
    }
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const userScore = score?.score || 750;
  const scorePercentage = (userScore / 1000) * 100;
  let scoreDescription = "Good";
  let scoreColor = colors.info;

  if (userScore >= 800) {
    scoreDescription = "Excellent";
    scoreColor = colors.success;
  } else if (userScore >= 700) {
    scoreDescription = "Good";
    scoreColor = colors.success;
  } else if (userScore >= 600) {
    scoreDescription = "Fair";
    scoreColor = colors.warning;
  } else {
    scoreDescription = "Needs Improvement";
    scoreColor = colors.warning;
  }

  const activeLoans = loans.filter((loan) => !loan.isRepaid && loan.isApproved);

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Credit Dashboard</Text>
        <TouchableOpacity
          onPress={() => navigation.navigate("Profile" as never)}
          style={styles.profileButton}
        >
          <Icon
            name="person"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.5)}
          />
        </TouchableOpacity>
      </View>

      {creditLoading && !score ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading your credit data...</Text>
        </View>
      ) : (
        <>
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
              <Text style={styles.statValue}>
                {score?.lastUpdated ? "5 years" : "New"}
              </Text>
            </View>
            <View style={styles.statCard}>
              <Icon
                name="account-balance"
                type="material"
                color={colors.warning}
                size={responsiveFontSize(3.5)}
              />
              <Text style={styles.statTitle}>Active Loans</Text>
              <Text style={styles.statValue}>{activeLoans.length}</Text>
            </View>
          </View>

          {scoreFactors.length > 0 && (
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
                    <Text style={styles.factorImpact}>
                      Impact: {factor.impact}
                    </Text>
                  </View>
                  <Text style={[styles.factorStatus, { color: factor.color }]}>
                    {factor.status}
                  </Text>
                </View>
              ))}
            </View>
          )}

          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => navigation.navigate("LoanCalculator" as never)}
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
              onPress={() => navigation.navigate("CreditHistory" as never)}
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
        </>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
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
  },
  profileButton: {
    padding: responsiveWidth(2),
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingVertical: responsiveHeight(10),
  },
  loadingText: {
    marginTop: responsiveHeight(2),
    fontSize: responsiveFontSize(1.8),
    color: colors.textSecondary,
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
  actionsContainer: {
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(4),
  },
  actionButton: {
    flexDirection: "row",
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
