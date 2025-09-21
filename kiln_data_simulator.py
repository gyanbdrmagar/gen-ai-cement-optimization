import time
import random
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- IMPORTANT SETUP INSTRUCTIONS ---
# 1. Go to your Firebase project settings -> Service accounts.
# 2. Click on "Generate new private key" to download a JSON file.
# 3. Rename this file to `serviceAccountKey.json` and place it in the same directory as this script.
# 4. Install the necessary Python library: `pip install firebase-admin`
# 5. Make sure you have a Firestore database set up in your Firebase project.

# Use a global variable to get the app ID from the environment.
# If not available, use a default value for local testing.
__app_id = "default-app-id" # Assuming the user will replace this if needed.

# Initialize the Firebase Admin SDK with the service account key.
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    print("Firebase Admin SDK initialized successfully.")
except FileNotFoundError:
    print("ERROR: `serviceAccountKey.json` not found. Please follow the setup instructions.")
    exit()

db = firestore.client()
# Use the security-compliant path for public data.
kiln_data_ref = db.collection(f"artifacts/{__app_id}/public/data/kiln_data")

# Simulated Kiln Parameters
# These are realistic values for a cement kiln.
# Reference: https://www.sciencedirect.com/topics/engineering/cement-kiln
kiln_temp_target = 1450.0  # Celsius
fuel_rate_base = 50.0     # Tons/hour
oxygen_level_target = 2.0 # Percent

def generate_data(anomaly=False):
    """
    Generates a dictionary with simulated kiln data.
    If anomaly is True, it introduces a problem.
    """
    data = {
        "timestamp": time.time(),
        "kiln_temp": kiln_temp_target + random.uniform(-5.0, 5.0),
        "fuel_rate": fuel_rate_base + random.uniform(-2.0, 2.0),
        "oxygen_level": oxygen_level_target + random.uniform(-0.5, 0.5),
        "quality_index": random.uniform(90.0, 100.0)
    }
    
    if anomaly:
        # Simulate an event causing a temperature drop.
        data["kiln_temp"] = random.uniform(1420.0, 1435.0)
        data["fuel_rate"] += random.uniform(-5.0, -1.0)
        data["oxygen_level"] += random.uniform(1.0, 3.0)
        print("--- ANOMALY DETECTED: Kiln temperature dropping! ---")
    else:
        print("Kiln operating in normal range.")
        
    return data

def main():
    """
    Main loop to simulate the data stream and write to Firestore.
    """
    # A single document to hold the latest kiln data for easy updates and retrieval.
    live_kiln_doc = kiln_data_ref.document("live_data")

    # A counter to introduce an anomaly after a certain number of cycles.
    anomaly_counter = 0
    anomaly_interval = 20  # Introduce an anomaly every 20 data points.

    print("Starting data simulation. Press Ctrl+C to stop.")
    try:
        while True:
            # Check for existing recommendation from the AI (front-end)
            current_doc = live_kiln_doc.get().to_dict()
            if current_doc and current_doc.get("ai_recommended_fuel_rate"):
                print("Applying AI-driven correction...")
                # Apply the AI's recommendation to the simulator's state
                new_fuel_rate = current_doc["ai_recommended_fuel_rate"]
                # Update the base fuel rate for subsequent data generation.
                global fuel_rate_base
                fuel_rate_base = new_fuel_rate
                # Reset the AI recommendation in the document to avoid re-applying it.
                live_kiln_doc.update({"ai_recommended_fuel_rate": firestore.DELETE_FIELD})
                
            # Generate new data, introducing an anomaly if the counter hits the interval.
            is_anomaly = (anomaly_counter % anomaly_interval == 0) and (anomaly_counter > 0)
            data_to_write = generate_data(anomaly=is_anomaly)
            
            # Write the new data to the Firestore document.
            live_kiln_doc.set(data_to_write, merge=True)
            print(f"Data written: {data_to_write}")
            
            anomaly_counter += 1
            time.sleep(2)  # Wait 2 seconds before the next data point.
            
    except KeyboardInterrupt:
        print("\nData simulation stopped.")
        
if __name__ == "__main__":
    main()
