// App.tsx
import { NavigationContainer } from "@react-navigation/native";
import AppNavigator from "./src/navigation/AppNavigator";
import { MedicationProvider } from "./src/store/medicationStore";

export default function App() {
  return (
    <MedicationProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </MedicationProvider>
  );
}
