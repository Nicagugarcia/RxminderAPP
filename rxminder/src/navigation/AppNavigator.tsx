import { createNativeStackNavigator } from "@react-navigation/native-stack";
import medicationMenu from "../screens/main/medicationMenu";
import createMedication from "../screens/main/createMedication";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  return (
    <Stack.Navigator>
      <Stack.Screen
        name="medicationMenu"
        component={medicationMenu}
        options={{ headerShown: false }}
      />
       <Stack.Screen
        name="createMedication"
        component={createMedication}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
