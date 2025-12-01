import { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from "react-native";
import { useAuth } from "../../store/authStore";

const BASE_URL = "http://127.0.0.1:8000";

export default function SubuserScreen() {
  const { currentUser } = useAuth();

  if (!currentUser) return null;

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [msg, setMsg] = useState("");

  const createSubuser = async () => {
    setMsg("");

    const res = await fetch(`${BASE_URL}/users/${currentUser.id}/subusers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });

    if (!res.ok) {
      setMsg("Failed to create subuser");
      return;
    }

    setMsg("Subuser created!");
    setEmail("");
    setUsername("");
    setPassword("");
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Add Subuser</Text>

      <TextInput
        style={styles.input}
        placeholder="Subuser Email"
        value={email}
        onChangeText={setEmail}
      />

      <TextInput
        style={styles.input}
        placeholder="Subuser Username"
        value={username}
        onChangeText={setUsername}
      />

      <TextInput
        style={styles.input}
        placeholder="Temporary Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      {msg !== "" && <Text>{msg}</Text>}

      <TouchableOpacity style={styles.button} onPress={createSubuser}>
        <Text style={styles.buttonText}>Create Subuser</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "white" },
  title: { fontSize: 26, fontWeight: "700", marginBottom: 20 },
  input: {
    borderWidth: 1, borderColor: "#ccc", borderRadius: 8,
    padding: 12, marginBottom: 12
  },
  button: {
    backgroundColor: "#2563eb",
    padding: 16, borderRadius: 10, alignItems: "center"
  },
  buttonText: { color: "white", fontWeight: "700", fontSize: 16 }
});
