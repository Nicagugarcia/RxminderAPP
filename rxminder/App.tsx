// App.tsx
import { NavigationContainer } from "@react-navigation/native";
import AppNavigator from "./src/navigation/AppNavigator";
import { MedicationProvider } from "./src/store/medicationStore";
import { AuthProvider } from "./src/store/authStore";

export default function App() {
  return (
    <AuthProvider>
      <MedicationProvider>
        <NavigationContainer>
          <AppNavigator />
        </NavigationContainer>
      </MedicationProvider>
    </AuthProvider>
  );
}
