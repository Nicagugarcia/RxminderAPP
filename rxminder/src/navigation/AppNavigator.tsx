import { createNativeStackNavigator } from "@react-navigation/native-stack";
import MedicationMenu from "../screens/main/medicationMenu";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="MedicationMenu"
        component={MedicationMenu}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
