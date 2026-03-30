import { useNavigation } from "@react-navigation/native";
import { Icon } from "@rneui/themed";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { logoutUser, updateWallet } from "../store/slices/authSlice";
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
  error: "#D0021B",
};

const ProfileScreen = () => {
  const navigation = useNavigation();
  const dispatch = useAppDispatch();
  const { user, isLoading } = useAppSelector((state) => state.auth);
  const [walletAddress, setWalletAddress] = useState(user?.walletAddress || "");
  const [isEditing, setIsEditing] = useState(false);

  const handleUpdateWallet = async () => {
    if (!walletAddress.trim()) {
      Alert.alert("Error", "Please enter a wallet address");
      return;
    }

    try {
      await dispatch(updateWallet(walletAddress)).unwrap();
      Alert.alert("Success", "Wallet address updated successfully");
      setIsEditing(false);
    } catch (error: any) {
      Alert.alert("Error", error || "Failed to update wallet address");
    }
  };

  const handleLogout = () => {
    Alert.alert("Logout", "Are you sure you want to logout?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Logout",
        style: "destructive",
        onPress: () => dispatch(logoutUser()),
      },
    ]);
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
        <Text style={styles.headerTitle}>Profile</Text>
        <View style={styles.headerPlaceholder} />
      </View>

      <View style={styles.profileCard}>
        <View style={styles.avatarContainer}>
          <Icon
            name="account-circle"
            type="material"
            color={colors.primary}
            size={responsiveFontSize(10)}
          />
        </View>
        <Text style={styles.username}>{user?.username}</Text>
        <Text style={styles.role}>{user?.role}</Text>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.sectionTitle}>Wallet Information</Text>
        <View style={styles.walletContainer}>
          <View style={styles.walletInputContainer}>
            <Icon
              name="account-balance-wallet"
              type="material"
              color={colors.textSecondary}
              size={responsiveFontSize(2.5)}
              containerStyle={styles.walletIcon}
            />
            <TextInput
              style={[styles.walletInput, !isEditing && styles.inputDisabled]}
              value={walletAddress}
              onChangeText={setWalletAddress}
              placeholder="No wallet connected"
              placeholderTextColor={colors.textSecondary}
              editable={isEditing}
            />
          </View>
          {isEditing ? (
            <View style={styles.editButtons}>
              <TouchableOpacity
                style={styles.saveButton}
                onPress={handleUpdateWallet}
                disabled={isLoading}
              >
                {isLoading ? (
                  <ActivityIndicator
                    color={colors.cardBackground}
                    size="small"
                  />
                ) : (
                  <Text style={styles.saveButtonText}>Save</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => {
                  setWalletAddress(user?.walletAddress || "");
                  setIsEditing(false);
                }}
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity
              style={styles.editButton}
              onPress={() => setIsEditing(true)}
            >
              <Icon
                name="edit"
                type="material"
                color={colors.primary}
                size={responsiveFontSize(2.2)}
              />
              <Text style={styles.editButtonText}>Edit</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Icon
          name="logout"
          type="material"
          color={colors.error}
          size={responsiveFontSize(2.5)}
        />
        <Text style={styles.logoutButtonText}>Logout</Text>
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
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
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
  },
  headerPlaceholder: {
    width: responsiveWidth(8),
  },
  profileCard: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginTop: responsiveHeight(3),
    marginBottom: responsiveHeight(2),
    padding: responsiveHeight(3),
    borderRadius: 15,
    alignItems: "center",
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  avatarContainer: {
    marginBottom: responsiveHeight(2),
  },
  username: {
    fontSize: responsiveFontSize(2.5),
    fontWeight: "bold",
    color: colors.textPrimary,
    marginBottom: responsiveHeight(0.5),
  },
  role: {
    fontSize: responsiveFontSize(1.8),
    color: colors.textSecondary,
    textTransform: "capitalize",
  },
  infoCard: {
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(2),
    padding: responsiveWidth(5),
    borderRadius: 15,
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  sectionTitle: {
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
    color: colors.textPrimary,
    marginBottom: responsiveHeight(2),
  },
  walletContainer: {
    marginBottom: responsiveHeight(1),
  },
  walletInputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.background,
    borderRadius: 10,
    paddingHorizontal: responsiveWidth(3),
    marginBottom: responsiveHeight(1.5),
  },
  walletIcon: {
    marginRight: responsiveWidth(2),
  },
  walletInput: {
    flex: 1,
    fontSize: responsiveFontSize(1.6),
    color: colors.textPrimary,
    paddingVertical: responsiveHeight(1.5),
  },
  inputDisabled: {
    color: colors.textSecondary,
  },
  editButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: responsiveHeight(1),
  },
  editButtonText: {
    color: colors.primary,
    fontSize: responsiveFontSize(1.8),
    fontWeight: "600",
    marginLeft: responsiveWidth(1),
  },
  editButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  saveButton: {
    flex: 1,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: responsiveHeight(1.5),
    alignItems: "center",
    marginRight: responsiveWidth(2),
  },
  saveButtonText: {
    color: colors.cardBackground,
    fontSize: responsiveFontSize(1.8),
    fontWeight: "bold",
  },
  cancelButton: {
    flex: 1,
    backgroundColor: colors.background,
    borderRadius: 10,
    paddingVertical: responsiveHeight(1.5),
    alignItems: "center",
    marginLeft: responsiveWidth(2),
  },
  cancelButtonText: {
    color: colors.textPrimary,
    fontSize: responsiveFontSize(1.8),
    fontWeight: "bold",
  },
  logoutButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.cardBackground,
    marginHorizontal: responsiveWidth(5),
    marginBottom: responsiveHeight(4),
    paddingVertical: responsiveHeight(1.8),
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.error,
  },
  logoutButtonText: {
    color: colors.error,
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
    marginLeft: responsiveWidth(2),
  },
});

export default ProfileScreen;
