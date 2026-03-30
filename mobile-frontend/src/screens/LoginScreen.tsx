import { Icon } from "@rneui/themed";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { clearError, loginUser } from "../store/slices/authSlice";
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

const LoginScreen = ({ navigation }: any) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const dispatch = useAppDispatch();
  const { isLoading, error } = useAppSelector((state) => state.auth);

  const handleLogin = async () => {
    if (!username.trim()) {
      Alert.alert("Error", "Please enter your username");
      return;
    }

    if (!password.trim()) {
      Alert.alert("Error", "Please enter your password");
      return;
    }

    try {
      await dispatch(loginUser({ username, password })).unwrap();
      // Navigation is handled in App.tsx based on auth state
    } catch (err: any) {
      Alert.alert("Login Failed", err || "Invalid credentials");
    }
  };

  const handleRegister = () => {
    dispatch(clearError());
    navigation.navigate("Register");
  };

  React.useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Icon
            name="account-balance-wallet"
            type="material"
            color={colors.primary}
            size={responsiveFontSize(8)}
          />
          <Text style={styles.title}>BlockScore</Text>
          <Text style={styles.subtitle}>Blockchain Credit Scoring</Text>
        </View>

        <View style={styles.formContainer}>
          <View style={styles.inputContainer}>
            <Icon
              name="person"
              type="material"
              color={colors.textSecondary}
              size={responsiveFontSize(2.5)}
              containerStyle={styles.inputIcon}
            />
            <TextInput
              style={styles.input}
              placeholder="Username"
              placeholderTextColor={colors.textSecondary}
              value={username}
              onChangeText={setUsername}
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          <View style={styles.inputContainer}>
            <Icon
              name="lock"
              type="material"
              color={colors.textSecondary}
              size={responsiveFontSize(2.5)}
              containerStyle={styles.inputIcon}
            />
            <TextInput
              style={styles.input}
              placeholder="Password"
              placeholderTextColor={colors.textSecondary}
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPassword}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TouchableOpacity
              onPress={() => setShowPassword(!showPassword)}
              style={styles.eyeIcon}
            >
              <Icon
                name={showPassword ? "visibility" : "visibility-off"}
                type="material"
                color={colors.textSecondary}
                size={responsiveFontSize(2.2)}
              />
            </TouchableOpacity>
          </View>

          {error && (
            <View style={styles.errorContainer}>
              <Icon
                name="error-outline"
                type="material"
                color={colors.error}
                size={responsiveFontSize(2)}
              />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <TouchableOpacity
            style={[styles.loginButton, isLoading && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color={colors.cardBackground} />
            ) : (
              <Text style={styles.loginButtonText}>Login</Text>
            )}
          </TouchableOpacity>

          <View style={styles.dividerContainer}>
            <View style={styles.divider} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.divider} />
          </View>

          <TouchableOpacity
            style={styles.registerButton}
            onPress={handleRegister}
            disabled={isLoading}
          >
            <Text style={styles.registerButtonText}>Create New Account</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: "center",
    paddingHorizontal: responsiveWidth(7),
    paddingVertical: responsiveHeight(5),
  },
  header: {
    alignItems: "center",
    marginBottom: responsiveHeight(5),
  },
  title: {
    fontSize: responsiveFontSize(4),
    fontWeight: "bold",
    color: colors.primary,
    marginTop: responsiveHeight(2),
  },
  subtitle: {
    fontSize: responsiveFontSize(1.8),
    color: colors.textSecondary,
    marginTop: responsiveHeight(1),
  },
  formContainer: {
    backgroundColor: colors.cardBackground,
    borderRadius: 20,
    padding: responsiveWidth(7),
    elevation: 5,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.background,
    borderRadius: 10,
    marginBottom: responsiveHeight(2),
    paddingHorizontal: responsiveWidth(3),
  },
  inputIcon: {
    marginRight: responsiveWidth(2),
  },
  input: {
    flex: 1,
    fontSize: responsiveFontSize(1.9),
    color: colors.textPrimary,
    paddingVertical: responsiveHeight(1.8),
  },
  eyeIcon: {
    padding: responsiveWidth(2),
  },
  errorContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#FFE5E5",
    padding: responsiveHeight(1.5),
    borderRadius: 8,
    marginBottom: responsiveHeight(2),
  },
  errorText: {
    color: colors.error,
    fontSize: responsiveFontSize(1.6),
    marginLeft: responsiveWidth(2),
    flex: 1,
  },
  loginButton: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: responsiveHeight(2),
    alignItems: "center",
    marginBottom: responsiveHeight(2),
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  loginButtonText: {
    color: colors.cardBackground,
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
  },
  dividerContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: responsiveHeight(2),
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: colors.border,
  },
  dividerText: {
    color: colors.textSecondary,
    marginHorizontal: responsiveWidth(3),
    fontSize: responsiveFontSize(1.6),
  },
  registerButton: {
    borderWidth: 2,
    borderColor: colors.primary,
    borderRadius: 10,
    paddingVertical: responsiveHeight(2),
    alignItems: "center",
  },
  registerButtonText: {
    color: colors.primary,
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
  },
});

export default LoginScreen;
