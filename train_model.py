import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

def load_and_preprocess_data(file_path):
    """
    Loads dataset from CSV and prepares features and target.
    """
    print(f"Loading dataset from {file_path}...")
    df = pd.read_csv(file_path)
    
    # Ensure no missing values
    if df.isnull().sum().sum() > 0:
        print("Warning: Missing values detected. Dropping rows with missing values.")
        df = df.dropna()
    
    # Separate features and target
    # 'user_id', 'timestamp', 'confidence' are metadata, not features
    X = df.drop(columns=["user_id", "mood_label", "timestamp", "confidence"], errors='ignore')
    y = df["mood_label"]
    
    return X, y

def train_production_model(X, y):
    """
    Trains a RandomForest classifier with specific hyperparameters.
    """
    # 80% train, 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print("Training RandomForest model...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,          # Prevent unlimited tree growth (was None → 100% train acc)
        min_samples_split=5,
        min_samples_leaf=5,    # Each leaf needs at least 5 samples — forces generalization
        max_features='sqrt',   # Standard RF: sqrt of features per split
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluation
    y_pred = model.predict(X_test)
    
    print("\n--- Model Evaluation ---")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    return model, X.columns.tolist()

def save_model(model, features, class_means, filename='model.pkl'):
    """
    Saves the model, feature metadata, and class distribution means for interpretability.
    """
    print(f"\nSaving model to {filename}...")
    # We save the model, feature names, and typical feature values per mood
    data_to_save = {
        'model': model,
        'features': features,
        'class_means': class_means
    }
    joblib.dump(data_to_save, filename)
    print("Model saved successfully.")

if __name__ == "__main__":
    DATA_PATH = 'backend/data/typing_behavior_dataset.csv'
    MODEL_OUT  = 'backend/model/model.pkl'

    # 1. Load Data
    X, y = load_and_preprocess_data(DATA_PATH)

    # 2. Train Model
    model, feature_names = train_production_model(X, y)

    # 3. Calculate Class Means (used for Feature Interpretability/Drivers in predictor.py)
    print("\nCalculating Class Profiles for ML Interpretability...")
    df_combined = X.copy()
    df_combined['mood_label'] = y
    class_means = df_combined.groupby('mood_label')[feature_names].mean().to_dict(orient='index')

    # 4. Save Model
    save_model(model, feature_names, class_means, filename=MODEL_OUT)
