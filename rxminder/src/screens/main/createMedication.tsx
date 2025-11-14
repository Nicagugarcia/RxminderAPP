import { useState } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { useMedications } from "../../store/medicationStore";
import DateTimePicker, {
  DateTimePickerEvent,
} from "@react-native-community/datetimepicker";
import { Platform } from "react-native";

export default function CreateMedication({ navigation }: any) {
  const { addMedication } = useMedications();

  const [name, setName] = useState("");
  const [dosage, setDosage] = useState("");
  const [frequency, setFrequency] = useState("");
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);
  const [notes, setNotes] = useState("");

  const handleAddMedication = () => {
    if (!name.trim()) return; // simple guard

    addMedication({
      name,
      dosage,
      frequency,
      startDate: startDate ? startDate.toISOString() : "",
      endDate: endDate ? endDate.toISOString() : "",
      notes,
    });

    navigation.goBack();
  };

  return (
    <View style={styles.container}>
    {/* Header with back button */}
    <View style={styles.header}>
      <TouchableOpacity onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>‹ Back</Text>
      </TouchableOpacity>
      <Text style={styles.headerTitle}>Add Medication</Text>
      <View style={{ width: 60 }} />
    </View>

      <ScrollView
        contentContainerStyle={styles.form}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.label}>Medication Name</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. Ibuprofen"
          value={name}
          onChangeText={setName}
        />

        <Text style={styles.label}>Dosage</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. 500 mg"
          value={dosage}
          onChangeText={setDosage}
        />

        <Text style={styles.label}>Frequency</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. 2 times per day"
          value={frequency}
          onChangeText={setFrequency}
        />

        {/* Start Date */}
        <Text style={styles.label}>Start Date</Text>
        <TouchableOpacity
          style={styles.input}
          onPress={() => setShowStartPicker(true)}
        >
          <Text>
            {startDate ? startDate.toDateString() : "Select start date"}
          </Text>
        </TouchableOpacity>
        {showStartPicker && (
          <DateTimePicker
            value={startDate || new Date()}
            mode="date"
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={(event: DateTimePickerEvent, selectedDate?: Date) => {
              setShowStartPicker(false);
              if (selectedDate) setStartDate(selectedDate);
            }}
          />
        )}

        {/* End Date */}
        <Text style={styles.label}>End Date</Text>
        <TouchableOpacity
          style={styles.input}
          onPress={() => setShowEndPicker(true)}
        >
          <Text>
            {endDate ? endDate.toDateString() : "Select end date"}
          </Text>
        </TouchableOpacity>
        {showEndPicker && (
          <DateTimePicker
            value={endDate || new Date()}
            mode="date"
            display={Platform.OS === "ios" ? "spinner" : "default"}
            onChange={(event: DateTimePickerEvent, selectedDate?: Date) => {
              setShowEndPicker(false);
              if (selectedDate) setEndDate(selectedDate);
            }}
          />
        )}


        <Text style={styles.label}>Notes</Text>
        <TextInput
          style={[styles.input, { height: 90, textAlignVertical: "top" }]}
          placeholder="Optional notes…"
          value={notes}
          onChangeText={setNotes}
          multiline
        />

        <TouchableOpacity style={styles.addButton} onPress={handleAddMedication}>
          <Text style={styles.addButtonText}>Add Medication</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
    paddingTop: 60,
    paddingHorizontal: 20,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 20,
    justifyContent: "space-between",
  },
  backText: {
    fontSize: 16,
    color: "#2563eb",
    fontWeight: "600",
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "700",
  },
  form: {
    paddingBottom: 40,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 6,
    marginTop: 12,
  },
  input: {
    borderWidth: 1,
    borderColor: "#e5e7eb",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
  },
  addButton: {
    marginTop: 24,
    backgroundColor: "#2563eb",
    paddingVertical: 16,
    borderRadius: 10,
    alignItems: "center",
  },
  addButtonText: {
    color: "#ffffff",
    fontSize: 18,
    fontWeight: "600",
  },
});
