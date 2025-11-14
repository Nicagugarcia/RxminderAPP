// src/screens/main/medicationMenu.tsx
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { useState } from "react";
import { useMedications } from "../../store/medicationStore";

export default function MedicationMenu({ navigation }: any) {
  const { medications, deleteMedication } = useMedications();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Medications</Text>

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
              <View style={styles.cardTextContainer}>
                <Text style={styles.cardTitle}>{med.name}</Text>
                <Text style={styles.cardText}>{med.dosage}</Text>
                <Text style={styles.cardText}>{med.frequency}</Text>
              </View>

              <View style={styles.cardMenuContainer}>
                <TouchableOpacity
                  onPress={() =>
                    setOpenMenuId(openMenuId === med.id ? null : med.id)
                  }
                >
                  <Text style={styles.menuDots}>⋯</Text>
                </TouchableOpacity>

                {openMenuId === med.id && (
                  <View style={styles.menu}>
                    <TouchableOpacity
                      onPress={() => {
                        setOpenMenuId(null);
                        navigation.navigate("EditMedication", { id: med.id });
                      }}
                    >
                      <Text style={styles.menuItem}>Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => {
                        deleteMedication(med.id);
                        setOpenMenuId(null);
                      }}
                    >
                      <Text style={[styles.menuItem, styles.deleteItem]}>
                        Delete
                      </Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            </View>
          ))}
        </ScrollView>
      )}

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
  list: {
    flex: 1,
  },
  card: {
    backgroundColor: "#f3f4f6",
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  cardTextContainer: {
    flexShrink: 1,
    paddingRight: 10,
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
  cardMenuContainer: {
    alignItems: "flex-end",
  },
  menuDots: {
    fontSize: 22,
    paddingHorizontal: 8,
  },
  menu: {
    marginTop: 4,
    backgroundColor: "white",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e5e7eb",
    paddingVertical: 4,
    minWidth: 100,
  },
  menuItem: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    fontSize: 14,
  },
  deleteItem: {
    color: "#b91c1c",
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
