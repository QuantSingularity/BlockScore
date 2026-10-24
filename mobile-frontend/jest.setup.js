/* eslint-env jest */
// Jest setup file
import "@testing-library/react-native/extend-expect";

// Mock AsyncStorage
jest.mock("@react-native-async-storage/async-storage", () =>
  require("@react-native-async-storage/async-storage/jest/async-storage-mock"),
);

// Mock react-native-vector-icons (both direct and @rneui's require(...).default usage)
jest.mock("react-native-vector-icons/MaterialIcons", () => ({
  __esModule: true,
  default: "Icon",
}));

jest.mock("react-native-chart-kit", () => ({
  LineChart: "LineChart",
  BarChart: "BarChart",
  PieChart: "PieChart",
}));

// Suppress console warnings during tests
global.console = {
  ...console,
  warn: jest.fn(),
  error: jest.fn(),
};
