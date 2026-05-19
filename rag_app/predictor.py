import joblib
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load all files once
model = joblib.load(os.path.join(BASE_DIR, "maize_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))
soil_encoder = joblib.load(os.path.join(BASE_DIR, "soil_encoder.pkl"))
fert_encoder = joblib.load(os.path.join(BASE_DIR, "fert_encoder.pkl"))


def predict_yield(data):
    """
    data = {
        "Latitude": float,
        "Longitude": float,
        "Soil_Type": str,
        "Fertilizer": str,
        "Pesticide_Amount": float,
        "Avg_Temp_C": float,
        "Rainfall_mm": float,
        "Humidity_%": float
    }
    """

    try:
        # Encode categorical
        soil = soil_encoder.transform([data["Soil_Type"]])[0]
        fert = fert_encoder.transform([data["Fertilizer"]])[0]

        # Arrange in correct order
        features = np.array([
            data["Latitude"],
            data["Longitude"],
            soil,
            fert,
            data["Pesticide_Amount"],
            data["Avg_Temp_C"],
            data["Rainfall_mm"],
            data["Humidity_%"]
        ]).reshape(1, -1)

        # Scale
        features = scaler.transform(features)

        # Predict
        prediction = model.predict(features)

        return float(prediction[0])

    except Exception as e:
        return str(e)