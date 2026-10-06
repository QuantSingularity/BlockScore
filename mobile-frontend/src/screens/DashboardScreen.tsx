import { useNavigation } from "@react-navigation/native";
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Icon } from "@rneui/themed";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  calculateScore,
  fetchCreditHistory,
  fetchCreditScore,
} from "../store/slices/creditSlice";
import { getScoringSummary } from "../services/credit.service";
import { fetchMyLoanApplications } from "../store/slices/loanSlice";
import {
  responsiveFontSize,
  responsiveHeight,
  responsiveWidth,
} from "../utils/responsive";
const colors = {
  primary: "#4A90E2",
  accent: "#50E3C2",
  background: "#F8F9FA",
  cardBackground: "#FFFFFF",
  textPrimary: "#333333",
  textSecondary: "#777777",
  border: "#EAEAEA",
  success: "#2ECC71",
  warning: "#F5A623",
  error: "#D0021B",
};
const SCORE_MIN = 300;
const SCORE_MAX = 850;
const gradeColor: Record<string, string> = {
  Excellent: colors.success,
  "Very Good": colors.success,
  Good: colors.primary,
  Fair: colors.warning,
  Poor: colors.error,
};
const DashboardScreen = () => {
  const navigation = useNavigation<any>();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const { score, scoreFactors, history, isLoading, error, needsWallet } =
    useAppSelector((state) => state.credit);
  const { applications } = useAppSelector((state) => state.loan);
  const [refreshing, setRefreshing] = useState(false);
  const [recalculating, setRecalculating] = useState(false);
  const walletAddress = user?.profile?.wallet_address || undefined;
  const loadDashboard = useCallback(() => {
    dispatch(fetchCreditScore(walletAddress));
    dispatch(fetchCreditHistory({ page: 1, perPage: 20 }));
    dispatch(fetchMyLoanApplications({ page: 1, perPage: 5 }));
  }, [dispatch, walletAddress]);
  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);
  const onRefresh = async () => {
    setRefreshing(true);
    loadDashboard();
    setRefreshing(false);
  };
  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      await dispatch(calculateScore(walletAddress)).unwrap();
    } catch (err: any) {
      Alert.alert("Error", err || "Failed to recalculate credit score");
    } finally {
      setRecalculating(false);
    }
  };
  const activeApplications = applications.filter((app) =>
    ["approved", "disbursed", "under_review", "submitted"].includes(app.status),
  ).length;
  if (isLoading && !score && !needsWallet) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading your dashboard...</Text>
      </View>
    );
  }
  const scoring = getScoringSummary(score);
  const scorePercentage = score
    ? ((score.score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN)) * 100
    : 0;
  const scoreColor = score
    ? gradeColor[score.score_grade] || colors.primary
    : colors.textSecondary;
  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>BlockScore</Text>
        <TouchableOpacity
          style={styles.profileButton}
          onPress={() => navigation.navigate("Profile")}
        >
          <Icon name="person" type="material" color={colors.cardBackground} />
        </TouchableOpacity>
      </View>

      {needsWallet ? (
        <View style={styles.walletPrompt}>
          <Icon
            name="account-balance-wallet"
            type="material"
            color={colors.primary}
            size={responsiveFontSize(4)}
          />
          <Text style={styles.walletPromptText}>
            Add a wallet address to your profile to calculate your credit score.
          </Text>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => navigation.navigate("Profile")}
          >
            <Text style={styles.actionButtonText}>Go to Profile</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
          {error ? (
            <View style={styles.walletPrompt}>
              <Icon name="error-outline" type="material" color={colors.error} />
              <Text style={styles.walletPromptText}>{error}</Text>
            </View>
          ) : (
            <View style={styles.scoreContainer}>
              <Text style={styles.scoreLabel}>Your Credit Score</Text>
              <Text style={[styles.scoreValue, { color: scoreColor }]}>
                {score?.score ?? "-"}
              </Text>
              <View style={styles.scoreBar}>
                <View
                  style={[
                    styles.scoreProgress,
                    {
                      width: `${Math.max(0, Math.min(100, scorePercentage))}%`,
                      backgroundColor: scoreColor,
                    },
                  ]}
                />
              </View>
              <Text style={[styles.scoreDescription, { color: scoreColor }]}>
                {score?.score_grade || "Not calculated"}
              </Text>
              <TouchableOpacity
                style={[styles.actionButton, styles.recalculateButton]}
                onPress={handleRecalculate}
                disabled={recalculating}
              >
                {recalculating ? (
                  <ActivityIndicator size="small" color={colors.primary} />
                ) : (
                  <>
                    <Icon
                      name="refresh"
                      type="material"
                      color={colors.primary}
                      size={responsiveFontSize(2)}
                      containerStyle={styles.buttonIcon}
                    />
                    <Text style={styles.recalculateButtonText}>
                      Recalculate
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}

          <View style={styles.statsContainer}>
            <View style={styles.statCard}>
              <Icon
                name="verified"
                type="material"
                color={colors.primary}
                size={responsiveFontSize(2.5)}
              />
              <Text style={styles.statTitle}>
                {scoring?.source === "rule_based"
                  ? "Rule Confidence"
                  : "Model Confidence"}
              </Text>
              <Text style={styles.statValue}>
                {scoring?.confidencePercent != null
                  ? `${scoring.confidencePercent}%`
                  : "-"}
              </Text>
            </View>
            <View style={styles.statCard}>
              <Icon
                name="history"
                type="material"
                color={colors.primary}
                size={responsiveFontSize(2.5)}
              />
              <Text style={styles.statTitle}>History Events</Text>
              <Text style={styles.statValue}>
                {history?.pagination?.total ?? 0}
              </Text>
            </View>
            <View style={styles.statCard}>
              <Icon
                name="account-balance"
                type="material"
                color={colors.primary}
                size={responsiveFontSize(2.5)}
              />
              <Text style={styles.statTitle}>Active Loans</Text>
              <Text style={styles.statValue}>{activeApplications}</Text>
            </View>
          </View>

          {scoring && scoring.source !== "unknown" && (
            <View style={styles.factorsContainer}>
              <Text style={styles.sectionTitle}>How This Score Was Made</Text>
              <Text style={styles.factorName}>{scoring.sourceLabel}</Text>
              {scoring.modelLabel ? (
                <Text style={styles.factorImpact}>{scoring.modelLabel}</Text>
              ) : null}
              {scoring.source === "rule_based" ? (
                <Text style={styles.factorImpact}>
                  The AI scoring service was unavailable or had no usable
                  history, so the built-in rules were used.
                </Text>
              ) : null}
              {scoring.positive.map((item) => (
                <View key={`pos-${item.factor}`} style={styles.insightRow}>
                  <Icon
                    name="trending-up"
                    type="material"
                    color={colors.success}
                    size={responsiveFontSize(2.2)}
                    containerStyle={styles.factorIcon}
                  />
                  <View style={styles.factorTextContainer}>
                    <Text style={styles.factorName}>{item.factor}</Text>
                    {item.description ? (
                      <Text style={styles.factorImpact}>
                        {item.description}
                      </Text>
                    ) : null}
                  </View>
                </View>
              ))}
              {scoring.negative.map((item) => (
                <View key={`neg-${item.factor}`} style={styles.insightRow}>
                  <Icon
                    name="trending-down"
                    type="material"
                    color={colors.error}
                    size={responsiveFontSize(2.2)}
                    containerStyle={styles.factorIcon}
                  />
                  <View style={styles.factorTextContainer}>
                    <Text style={styles.factorName}>{item.factor}</Text>
                    {item.description ? (
                      <Text style={styles.factorImpact}>
                        {item.description}
                      </Text>
                    ) : null}
                  </View>
                </View>
              ))}
            </View>
          )}

          {scoreFactors.length > 0 && (
            <View style={styles.factorsContainer}>
              <Text style={styles.sectionTitle}>Score Factors</Text>
              {scoreFactors.map((factor, index) => (
                <View key={`${factor.name}-${index}`} style={styles.factorItem}>
                  <Icon
                    name="insights"
                    type="material"
                    color={colors.primary}
                    size={responsiveFontSize(2.2)}
                    containerStyle={styles.factorIcon}
                  />
                  <View style={styles.factorTextContainer}>
                    <Text style={styles.factorName}>{factor.name}</Text>
                    {factor.description ? (
                      <Text style={styles.factorImpact}>
                        {factor.description}
                      </Text>
                    ) : null}
                  </View>
                  <Text
                    style={[
                      styles.factorStatus,
                      {
                        color:
                          factor.value >= 70
                            ? colors.success
                            : factor.value >= 40
                              ? colors.warning
                              : colors.error,
                      },
                    ]}
                  >
                    {factor.value}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </>
      )}

      <View style={styles.actionsContainer}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("LoanCalculator")}
        >
          <Icon
            name="calculate"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.2)}
            containerStyle={styles.buttonIcon}
          />
          <Text style={styles.actionButtonText}>Loan Calculator</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate("CreditHistory")}
        >
          <Icon
            name="receipt-long"
            type="material"
            color={colors.cardBackground}
            size={responsiveFontSize(2.2)}
            containerStyle={styles.buttonIcon}
          />
          <Text style={styles.actionButtonText}>View Credit History</Text>
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
  insightRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingTop: responsiveHeight(1.5),
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
  walletPrompt: {
    alignItems: "center",
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginTop: responsiveHeight(3),
    marginBottom: responsiveHeight(2),
    padding: responsiveHeight(3),
    borderRadius: 15,
    elevation: 3,
  },
  walletPromptText: {
    fontSize: responsiveFontSize(1.9),
    color: colors.textSecondary,
    textAlign: "center",
    marginVertical: responsiveHeight(2),
  },
  recalculateButton: {
    flexDirection: "row",
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.primary,
    paddingVertical: responsiveHeight(1.2),
    paddingHorizontal: responsiveWidth(4),
    marginTop: responsiveHeight(2),
    marginBottom: 0,
    elevation: 0,
    shadowOpacity: 0,
  },
  recalculateButtonText: {
    color: colors.primary,
    fontSize: responsiveFontSize(1.8),
    fontWeight: "600",
  },
});
export default DashboardScreen;
