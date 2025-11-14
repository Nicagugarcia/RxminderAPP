import { createNativeStackNavigator } from "@react-navigation/native-stack";
import MedicationMenu from "../screens/main/medicationMenu";
import createMedication from "../screens/main/createMedication";
import editMedication from "../screens/main/editMedication"; // NEW

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="MedicationMenu"
        component={MedicationMenu}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="CreateMedication"
        component={createMedication}
        options={{ headerShown: false }}
      />
      <Stack.Screen
        name="EditMedication"
        component={editMedication}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
