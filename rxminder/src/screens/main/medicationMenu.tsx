import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { useMedications } from "../../store/medicationStore";

export default function MedicationMenu({ navigation }: any) {
  const { medications } = useMedications();

  return (
    <View style={styles.container}>
      {/* Title */}
      <Text style={styles.title}>Medications</Text>

      {/* List or empty state */}
      {medications.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No medications yet</Text>
        </View>
      ) : (
        <ScrollView
          style={styles.list}
          contentContainerStyle={{ paddingBottom: 20 }}
        >
          {medications.map((med) => (
            <View key={med.id} style={styles.card}>
              <Text style={styles.cardTitle}>{med.name}</Text>
              <Text style={styles.cardText}>{med.dosage}</Text>
              <Text style={styles.cardText}>{med.frequency}</Text>
            </View>
          ))}
        </ScrollView>
      )}

      {/* Add button */}
      <TouchableOpacity
        style={styles.addButton}
        onPress={() => navigation.navigate("createMedication")}
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
  list: {
    flex: 1,
  },
  card: {
    backgroundColor: "#f3f4f6",
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 4,
  },
  cardText: {
    fontSize: 14,
    color: "#4b5563",
  },
  addButton: {
    backgroundColor: "#2563eb",
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
