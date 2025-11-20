// src/store/medicationStore.tsx
import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { getPrescriptions, createPrescription, updatePrescription, deletePrescription } from "../utils/api";

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
  addMedication: (med: Omit<Medication, "id">) => Promise<void>;
  updateMedication: (id: string, med: Omit<Medication, "id">) => Promise<void>;
  deleteMedication: (id: string) => Promise<void>;
};

const MedicationContext = createContext<MedicationContextType | undefined>(
  undefined
);

export function MedicationProvider({ children }: { children: ReactNode }) {
  const [medications, setMedications] = useState<Medication[]>([]);
  // Map a backend prescription list entry -> local Medication shape
  const entryToMedication = (entry: any): Medication => {
    const med = entry.medication ?? {};
    const sched = entry.schedule ?? {};
    return {
      id: String(med.id ?? Date.now()),
      name: med.drug_name ?? "",
      dosage: med.dosage ?? "",
      frequency: String(med.frequency ?? ""),
      startDate: sched.start_date ? new Date(sched.start_date).toISOString() : "",
      endDate: sched.end_date ? new Date(sched.end_date).toISOString() : "",
      notes: med.message ?? "",
    };
  };

  // Load prescriptions from backend on mount (dev: user_id = 1)
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const list = await getPrescriptions(1);
        if (!mounted) return;
        const local = Array.isArray(list) ? list.map(entryToMedication) : [];
        setMedications(local);
      } catch (err) {
        console.error("Failed to load prescriptions from backend:", err);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  

  const addMedication = async (med: Omit<Medication, "id">) => {
    // Build backend payload from UI Medication
    const formatDate = (s: string | undefined) => {
      if (!s) return undefined;
      try {
        return new Date(s).toISOString().slice(0, 10);
      } catch {
        return undefined;
      }
    };

    const payload = {
      user_id: 1, // development user
      drug_name: med.name?.trim(),
      dosage: med.dosage?.trim() || "1",
      frequency: Number(med.frequency) || 1,
      start_date: formatDate(med.startDate) || new Date().toISOString().slice(0, 10),
      end_date: formatDate(med.endDate) ?? undefined,
      start_time: "08:00",
      message: med.notes?.trim() || undefined,
    };

    try {
      const resp = await createPrescription(payload);
      // resp contains medication and schedule
      const backendMed = resp.medication ?? {};
      const schedule = resp.schedule ?? {};

      const newLocal: Medication = {
        id: String(backendMed.id ?? Date.now()),
        name: backendMed.drug_name ?? med.name,
        dosage: backendMed.dosage ?? med.dosage,
        frequency: String(backendMed.frequency ?? med.frequency),
        startDate: schedule.start_date ? new Date(schedule.start_date).toISOString() : med.startDate,
        endDate: schedule.end_date ? new Date(schedule.end_date).toISOString() : med.endDate,
        notes: backendMed.message ?? med.notes,
      };

      setMedications((prev) => [...prev, newLocal]);
    } catch (err) {
      console.error("createPrescription failed", err);
      throw err;
    }
  };

  const updateMedication = async (id: string, med: Omit<Medication, "id">) => {
    const formatDate = (s: string | undefined) => {
      if (!s) return undefined;
      try {
        return new Date(s).toISOString().slice(0, 10);
      } catch {
        return undefined;
      }
    };

    // build partial payload: only include keys that are set
    const rawPayload: any = {
      drug_name: med.name?.trim(),
      dosage: med.dosage?.trim() || undefined,
      frequency: med.frequency ? Number(med.frequency) : undefined,
      start_date: formatDate(med.startDate) || undefined,
      end_date: formatDate(med.endDate) ?? undefined,
      // keep a default start_time unless UI provides one later
      start_time: "08:00",
      message: med.notes?.trim() || undefined,
    };

    // remove undefined fields so we send a minimal partial update
    const payload: any = {};
    Object.entries(rawPayload).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") payload[k] = v;
    });

    try {
      const resp = await updatePrescription(Number(id), payload);
      const backendMed = resp.medication ?? {};
      const schedule = resp.schedule ?? {};

      const updatedLocal: Medication = {
        id: String(backendMed.id ?? id),
        name: backendMed.drug_name ?? med.name,
        dosage: backendMed.dosage ?? med.dosage,
        frequency: String(backendMed.frequency ?? med.frequency),
        startDate: schedule.start_date ? new Date(schedule.start_date).toISOString() : med.startDate,
        endDate: schedule.end_date ? new Date(schedule.end_date).toISOString() : med.endDate,
        notes: backendMed.message ?? med.notes,
      };

      setMedications((prev) => prev.map((m) => (m.id === id ? updatedLocal : m)));
    } catch (err) {
      console.error("updatePrescription failed", err);
      throw err;
    }
  };

  const deleteMedication = async (id: string) => {
    try {
      await deletePrescription(Number(id));
      setMedications((prev) => prev.filter((m) => m.id !== id));
    } catch (err) {
      console.error("deletePrescription failed", err);
      throw err;
    }
  };

  return (
    <MedicationContext.Provider
      value={{ medications, addMedication, updateMedication, deleteMedication }}
    >
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
