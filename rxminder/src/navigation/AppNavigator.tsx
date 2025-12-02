import { createNativeStackNavigator } from "@react-navigation/native-stack";
import loginScreen from "../screens/auth/loginScreen";
import medicationMenu from "../screens/main/medicationMenu";
import createMedication from "../screens/main/createMedication";
import editMedication from "../screens/main/editMedication";
import subuserScreen from "../screens/main/subuserScreen";
import pharmacyLocatorScreen from "../screens/main/pharmacyLocatorScreen";
import { useAuth } from "../store/authStore";

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  const { currentUser } = useAuth();

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {!currentUser ? (
        <Stack.Screen name="Login" component={loginScreen} />
      ) : (
        <>
          <Stack.Screen name="MedicationMenu" component={medicationMenu} />
          <Stack.Screen name="CreateMedication" component={createMedication} />
          <Stack.Screen name="EditMedication" component={editMedication} />
          <Stack.Screen name="Subusers" component={subuserScreen} options={{headerShown: true, title: "Add Subuser",}}/>
          <Stack.Screen name="PharmacyLocator" component={pharmacyLocatorScreen} />
        </>
      )}
    </Stack.Navigator>
  );
}