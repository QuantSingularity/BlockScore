import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useEffect } from "react";
import { Provider } from "react-redux";
import CreditHistoryScreen from "./src/screens/CreditHistoryScreen";
import DashboardScreen from "./src/screens/DashboardScreen";
import LoanCalculatorScreen from "./src/screens/LoanCalculatorScreen";

// Screens
import LoginScreen from "./src/screens/LoginScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import RegisterScreen from "./src/screens/RegisterScreen";
import { store } from "./src/store";
import { useAppDispatch, useAppSelector } from "./src/store/hooks";
import { checkStoredAuth } from "./src/store/slices/authSlice";

const Stack = createNativeStackNavigator();

const AppNavigator = () => {
  const dispatch = useAppDispatch();
  const { isAuthenticated } = useAppSelector((state) => state.auth);

  useEffect(() => {
    dispatch(checkStoredAuth());
  }, [dispatch]);

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!isAuthenticated ? (
        <>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
        </>
      ) : (
        <>
          <Stack.Screen name="Dashboard" component={DashboardScreen} />
          <Stack.Screen name="CreditHistory" component={CreditHistoryScreen} />
          <Stack.Screen
            name="LoanCalculator"
            component={LoanCalculatorScreen}
          />
          <Stack.Screen name="Profile" component={ProfileScreen} />
        </>
      )}
    </Stack.Navigator>
  );
};

const App = () => {
  return (
    <Provider store={store}>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </Provider>
  );
};

export default App;
