// src/store/medicationStore.tsx
import { createContext, useContext, useState, ReactNode } from "react";

export type Medication = {
  id: string;
  name: string;
  dosage: string;
  frequency: string;
  startDate: string;
  endDate: string;
  notes: string;
};

type MedicationContextType = {
  medications: Medication[];
  addMedication: (med: Omit<Medication, "id">) => void;
};

const MedicationContext = createContext<MedicationContextType | undefined>(
  undefined
);

export function MedicationProvider({ children }: { children: ReactNode }) {
  const [medications, setMedications] = useState<Medication[]>([]);

  const addMedication = (med: Omit<Medication, "id">) => {
    setMedications((prev) => [
      ...prev,
      { id: Date.now().toString(), ...med },
    ]);
  };

  return (
    <MedicationContext.Provider value={{ medications, addMedication }}>
      {children}
    </MedicationContext.Provider>
  );
}

export function useMedications() {
  const ctx = useContext(MedicationContext);
  if (!ctx) {
    throw new Error("useMedications must be used within MedicationProvider");
  }
  return ctx;
}
