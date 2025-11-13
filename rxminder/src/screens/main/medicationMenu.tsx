// src/screens/Main/MedicationMenu.tsx
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

export default function MedicationMenu({ navigation }: any) {
  return (
    <View style={styles.container}>
      {/* Title */}
      <Text style={styles.title}>Medications</Text>

      {/* Empty state for now */}
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>No medications yet</Text>
      </View>

      {/* Add Medication button */}
      <TouchableOpacity
        style={styles.addButton}
        onPress={() => navigation.navigate("CreateMedication")}
      >
        <Text style={styles.addButtonText}>+ Add Medication</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
    paddingHorizontal: 20,
    paddingTop: 60,
  },

  title: {
    fontSize: 32,
    fontWeight: "700",
    marginBottom: 20,
  },

  emptyContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },

  emptyText: {
    fontSize: 16,
    color: "#6b7280",
  },

  addButton: {
    backgroundColor: "#2563eb", // blue
    paddingVertical: 16,
    borderRadius: 10,
    marginBottom: 30,
    alignItems: "center",
  },

  addButtonText: {
    color: "white",
    fontSize: 18,
    fontWeight: "600",
  },
});
