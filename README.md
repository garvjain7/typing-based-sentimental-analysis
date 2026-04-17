# ⌨️ Typing Mood Analyzer

Typing Mood Analyzer is a full-stack Machine Learning application that predicts a user's mood (Happy, Neutral, or Stressed) based entirely on their typing behavior. 

Instead of analyzing *what* you type, this application analyzes *how* you type, deriving deep behavioral insights from keystroke dynamics such as Words Per Minute (WPM), Error Rates, Pause Variability, and Key Hold Times.

## 🚀 Features

*   **Live Keystroke Tracking:** Real-time capture of typing pace, gaps, and corrections.
*   **Behavioral Feature Engineering:** Translates raw keydown/keyup events into 12 distinct machine-learning features (e.g. Burstiness Score, Typing Consistency).
*   **Random Forest Classifier:** A high-accuracy ML model (`scikit-learn`) trained to classify mood without needing semantic context.
*   **AI Reasoning (Interpretability):** The UI unpacks the model's prediction, showing the top 3 driving factors for *why* it made that prediction (e.g., `⚡ High Error Rate`, `⚡ Low WPM`).
*   **Synthetic Data Generation:** Includes a robust script to organically generate realistic typing behaviors for training variations.

## 📂 Project Structure

```text
typing-sentimental-analyzer/
│
├── app.py                      # FastAPI web server
├── generate_dataset.py         # Synthetic data generation tool
├── train_model.py              # ML training script for RandomForest
├── paragraphs.txt              # Text prompts the user can copy
│
├── backend/
│   ├── features.py             # Translates raw JS data into ML features
│   ├── predictor.py            # AI Engine handling inference & driving factors
│   ├── storage.py              # Live user DB appender
│   ├── data/
│   │   └── typing_behavior_dataset.csv  # The master dataset
│   └── model/
│       └── model.pkl           # Compiled model + baseline class means
│
└── frontend/
    ├── templates/
    │   └── index.html          # Main HTML Dashboard
    └── static/
        ├── css/style.css       # Visual styling
        └── js/
            ├── api.js          # Fetch routing
            ├── metrics.js      # Raw calculation of time differences
            ├── typing.js       # Core logic handling DOM and keystrokes
            └── utils.js        # Support functions
```

## 🛠️ Usage Setup

1. **Install Dependencies**
Ensure you have Python 3 installed. Install the requirements (FastAPI, Uvicorn, Pandas, Scikit-learn, Joblib):
```bash
pip install fastapi uvicorn pandas scikit-learn joblib jinja2 python-multipart
```

2. **(Optional) Re-train the Model**
If you want to train the model from scratch on the provided dataset:
```bash
python train_model.py
```

3. **Run the Server**
Start the FastAPI dashboard on `localhost`:
```bash
python app.py
```
Open `http://localhost:5000` in your web browser.

## 🧠 How it Works
When a user begins typing, JavaScript captures timing events (`keydown`, `keyup`, and input corrections). When finished, it submits a payload to the FastAPI backend. 

The backend normalizes this data into a DataFrame. The Random Forest model compares these exact features against baseline distributions it learned during training, arriving at a final mood prediction. It then calculates mathematical deviations to tell the frontend exactly which behavioral factors swayed the decision.
