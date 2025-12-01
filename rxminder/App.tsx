// App.tsx
import React, { useEffect } from "react";
import { NavigationContainer } from "@react-navigation/native";
import AppNavigator from "./src/navigation/AppNavigator";
import { MedicationProvider } from "./src/store/medicationStore";
<<<<<<< HEAD
import { AuthProvider } from "./src/store/authStore";
=======
import * as Notifications from "expo-notifications";
import { registerAndScheduleForUser, getAllLocalMappings } from "./src/utils/notifications";
>>>>>>> main

export default function App() {
  useEffect(() => {
    // replace `1` with the authenticated user id when available
    (async function initNotifications() {
      try {
        console.log("initNotifications: starting registration/scheduling");
        await registerAndScheduleForUser(1);
        console.log("initNotifications: registerAndScheduleForUser resolved");
      } catch (e) {
        // ignore registration errors for now
      }

      // // print scheduled notifications and stored mappings for debugging
      // try {
      //   console.log("Fetching scheduled local notifications for debugging...");
      //   const scheduled = await Notifications.getAllScheduledNotificationsAsync();
      //   console.log("Scheduled local notifications:", scheduled);
      // } catch (e) {
      //   console.log("Failed to get scheduled notifications:", e);
      // }

      // try {
      //   const mappings = await getAllLocalMappings();
      //   console.log("Reminder -> localId mappings:", mappings);
      // } catch (e) {
      //   console.log("Failed to get local mappings:", e);
      // }
    })();
  }, []);

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
