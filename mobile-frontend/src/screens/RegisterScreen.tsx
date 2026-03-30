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
import { clearError, registerUser } from "../store/slices/authSlice";
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
  success: "#50E3C2",
};

const RegisterScreen = ({ navigation }: any) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const dispatch = useAppDispatch();
  const { isLoading, error } = useAppSelector((state) => state.auth);

  const handleRegister = async () => {
    if (!username.trim()) {
      Alert.alert("Error", "Please enter a username");
      return;
    }

    if (username.length < 3) {
      Alert.alert("Error", "Username must be at least 3 characters");
      return;
    }

    if (!password.trim()) {
      Alert.alert("Error", "Please enter a password");
      return;
    }

    if (password.length < 6) {
      Alert.alert("Error", "Password must be at least 6 characters");
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert("Error", "Passwords do not match");
      return;
    }

    try {
      await dispatch(registerUser({ username, password })).unwrap();
      Alert.alert("Success", "Account created successfully! Please log in.", [
        {
          text: "OK",
          onPress: () => navigation.navigate("Login"),
        },
      ]);
    } catch (err: any) {
      Alert.alert("Registration Failed", err || "Could not create account");
    }
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
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <Icon
              name="arrow-back-ios"
              type="material"
              color={colors.primary}
              size={responsiveFontSize(2.5)}
            />
          </TouchableOpacity>
          <Icon
            name="person-add"
            type="material"
            color={colors.primary}
            size={responsiveFontSize(6)}
          />
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join BlockScore today</Text>
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

          <View style={styles.inputContainer}>
            <Icon
              name="lock-outline"
              type="material"
              color={colors.textSecondary}
              size={responsiveFontSize(2.5)}
              containerStyle={styles.inputIcon}
            />
            <TextInput
              style={styles.input}
              placeholder="Confirm Password"
              placeholderTextColor={colors.textSecondary}
              value={confirmPassword}
              onChangeText={setConfirmPassword}
              secureTextEntry={!showConfirmPassword}
              autoCapitalize="none"
              autoCorrect={false}
            />
            <TouchableOpacity
              onPress={() => setShowConfirmPassword(!showConfirmPassword)}
              style={styles.eyeIcon}
            >
              <Icon
                name={showConfirmPassword ? "visibility" : "visibility-off"}
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
            style={[styles.registerButton, isLoading && styles.buttonDisabled]}
            onPress={handleRegister}
            disabled={isLoading}
          >
            {isLoading ? (
              <ActivityIndicator color={colors.cardBackground} />
            ) : (
              <Text style={styles.registerButtonText}>Create Account</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.loginLink}
            onPress={() => navigation.navigate("Login")}
            disabled={isLoading}
          >
            <Text style={styles.loginLinkText}>
              Already have an account?{" "}
              <Text style={styles.loginLinkBold}>Login</Text>
            </Text>
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
    marginBottom: responsiveHeight(4),
  },
  backButton: {
    position: "absolute",
    left: 0,
    top: 0,
    padding: responsiveWidth(2),
  },
  title: {
    fontSize: responsiveFontSize(3.5),
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
  registerButton: {
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: responsiveHeight(2),
    alignItems: "center",
    marginBottom: responsiveHeight(2),
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  registerButtonText: {
    color: colors.cardBackground,
    fontSize: responsiveFontSize(2),
    fontWeight: "bold",
  },
  loginLink: {
    alignItems: "center",
    paddingVertical: responsiveHeight(1),
  },
  loginLinkText: {
    color: colors.textSecondary,
    fontSize: responsiveFontSize(1.7),
  },
  loginLinkBold: {
    color: colors.primary,
    fontWeight: "bold",
  },
});

export default RegisterScreen;
