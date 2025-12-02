// src/screens/main/pharmacyLocatorScreen.tsx
import { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
} from "react-native";
import MapView, { Marker, PROVIDER_GOOGLE } from "react-native-maps";
import * as Location from "expo-location";
import { getPharmacies, Pharmacy } from "../../utils/api";

export default function PharmacyLocatorScreen({ navigation }: any) {
  const [location, setLocation] = useState<Location.LocationObject | null>(null);
  const [pharmacies, setPharmacies] = useState<Pharmacy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedPharmacy, setSelectedPharmacy] = useState<Pharmacy | null>(null);
  const [radius, setRadius] = useState(5000); // 5km default

  useEffect(() => {
    loadPharmacies();
  }, []);

  const loadPharmacies = async () => {
    setLoading(true);
    setError("");

    try {
      // Request location permission
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        setError("Location permission denied");
        setLoading(false);
        return;
      }

      // Get current location
      const currentLocation = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setLocation(currentLocation);

      // Fetch nearby pharmacies
      const result = await getPharmacies(
        currentLocation.coords.latitude,
        currentLocation.coords.longitude,
        radius
      );

      if (result.status === "OK") {
        setPharmacies(result.pharmacies);
      } else {
        setError(`Failed to fetch pharmacies: ${result.status}`);
      }
    } catch (err: any) {
      console.error("loadPharmacies error:", err);
      setError(err.message || "Failed to load pharmacies");
    } finally {
      setLoading(false);
    }
  };

  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    // Haversine formula for distance in kilometers
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const openNavigation = (pharmacy: Pharmacy) => {
    const scheme = Platform.select({
      ios: "maps:",
      android: "geo:",
    });
    const url = Platform.select({
      ios: `${scheme}0,0?q=${pharmacy.latitude},${pharmacy.longitude}(${encodeURIComponent(
        pharmacy.name
      )})`,
      android: `${scheme}${pharmacy.latitude},${pharmacy.longitude}?q=${pharmacy.latitude},${pharmacy.longitude}(${encodeURIComponent(
        pharmacy.name
      )})`,
    });

    if (url) {
      Linking.openURL(url).catch(() =>
        Alert.alert("Error", "Unable to open maps application")
      );
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
        <Text style={styles.loadingText}>Finding nearby pharmacies...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadPharmacies}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>‹ Back</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Nearby Pharmacies</Text>
        <TouchableOpacity onPress={loadPharmacies}>
          <Text style={styles.refreshText}>↻</Text>
        </TouchableOpacity>
      </View>

      {/* Map View */}
      {location && (
        <MapView
          style={styles.map}
          provider={PROVIDER_GOOGLE}
          initialRegion={{
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            latitudeDelta: 0.05,
            longitudeDelta: 0.05,
          }}
          showsUserLocation
          showsMyLocationButton
        >
          {pharmacies.map((pharmacy) => (
            <Marker
              key={pharmacy.place_id}
              coordinate={{
                latitude: pharmacy.latitude,
                longitude: pharmacy.longitude,
              }}
              title={pharmacy.name}
              description={pharmacy.address}
              onPress={() => setSelectedPharmacy(pharmacy)}
              pinColor="#10b981"
            />
          ))}
        </MapView>
      )}

      {/* Pharmacy List */}
      <View style={styles.listContainer}>
        <Text style={styles.listTitle}>
          {pharmacies.length} pharmacies found
        </Text>
        <ScrollView style={styles.list} showsVerticalScrollIndicator={false}>
          {pharmacies.map((pharmacy) => {
            const distance = location
              ? calculateDistance(
                  location.coords.latitude,
                  location.coords.longitude,
                  pharmacy.latitude,
                  pharmacy.longitude
                )
              : 0;

            return (
              <TouchableOpacity
                key={pharmacy.place_id}
                style={[
                  styles.pharmacyCard,
                  selectedPharmacy?.place_id === pharmacy.place_id &&
                    styles.selectedCard,
                ]}
                onPress={() => setSelectedPharmacy(pharmacy)}
              >
                <View style={styles.pharmacyInfo}>
                  <Text style={styles.pharmacyName}>{pharmacy.name}</Text>
                  <Text style={styles.pharmacyAddress}>{pharmacy.address}</Text>
                  <View style={styles.pharmacyMeta}>
                    <Text style={styles.distance}>
                      {distance.toFixed(1)} km away
                    </Text>
                    {pharmacy.rating && (
                      <Text style={styles.rating}>⭐ {pharmacy.rating}</Text>
                    )}
                    {pharmacy.open_now !== undefined && (
                      <Text
                        style={[
                          styles.openStatus,
                          pharmacy.open_now
                            ? styles.openNow
                            : styles.closedNow,
                        ]}
                      >
                        {pharmacy.open_now ? "Open" : "Closed"}
                      </Text>
                    )}
                  </View>
                </View>
                <TouchableOpacity
                  style={styles.navigateButton}
                  onPress={() => openNavigation(pharmacy)}
                >
                  <Text style={styles.navigateButtonText}>Navigate</Text>
                </TouchableOpacity>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 15,
    backgroundColor: "#ffffff",
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
  },
  backText: {
    fontSize: 18,
    color: "#2563eb",
    fontWeight: "600",
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "700",
  },
  refreshText: {
    fontSize: 24,
    color: "#2563eb",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: "#6b7280",
  },
  errorText: {
    fontSize: 16,
    color: "#dc2626",
    textAlign: "center",
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: "#2563eb",
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 12,
  },
  retryButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "600",
  },
  backButton: {
    paddingVertical: 12,
    paddingHorizontal: 24,
  },
  backButtonText: {
    color: "#6b7280",
    fontSize: 16,
  },
  map: {
    height: 300,
  },
  listContainer: {
    flex: 1,
    backgroundColor: "#f9fafb",
    paddingTop: 16,
  },
  listTitle: {
    fontSize: 16,
    fontWeight: "600",
    paddingHorizontal: 20,
    marginBottom: 12,
    color: "#374151",
  },
  list: {
    flex: 1,
    paddingHorizontal: 20,
  },
  pharmacyCard: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  selectedCard: {
    borderWidth: 2,
    borderColor: "#2563eb",
  },
  pharmacyInfo: {
    flex: 1,
    marginRight: 12,
  },
  pharmacyName: {
    fontSize: 16,
    fontWeight: "700",
    color: "#111827",
    marginBottom: 4,
  },
  pharmacyAddress: {
    fontSize: 14,
    color: "#6b7280",
    marginBottom: 8,
  },
  pharmacyMeta: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  distance: {
    fontSize: 12,
    color: "#2563eb",
    fontWeight: "600",
  },
  rating: {
    fontSize: 12,
    color: "#f59e0b",
  },
  openStatus: {
    fontSize: 12,
    fontWeight: "600",
  },
  openNow: {
    color: "#10b981",
  },
  closedNow: {
    color: "#dc2626",
  },
  navigateButton: {
    backgroundColor: "#2563eb",
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  navigateButtonText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "600",
  },
});