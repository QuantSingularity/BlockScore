import { StyleSheet, Text, View } from "react-native";
import { responsiveFontSize } from "../utils/responsive";

const HomeScreen = ({ navigation }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>BlockScore Home</Text>
      {/* Add buttons or links to navigate to other screens */}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  title: {
    fontSize: responsiveFontSize(3),
    fontWeight: "bold",
    marginBottom: 20,
  },
});

export default HomeScreen;
