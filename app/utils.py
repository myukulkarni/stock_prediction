import matplotlib
matplotlib.use('Agg')  # Prevents GUI issues in threads

import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
import numpy as np
import os

from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model
from datetime import datetime
from django.conf import settings
from app.models import Prediction  # ✅ Import your Prediction model


def run_prediction(ticker, user=None):
    """
    Predicts the stock price and saves result to DB if user is passed.
    """

    # Step 1: Download stock data
    data = yf.download(ticker, period='10y')
    if data.empty:
        raise ValueError("Invalid or unavailable ticker symbol.")

    df = data[['Close']].dropna()

    # Step 2: Scale the data
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)

    # Step 3: Prepare input
    X_test = [scaled_data[i-60:i] for i in range(60, len(scaled_data))]
    X_test = np.array(X_test).reshape(-1, 60, 1)

    # Step 4: Load trained model
    model_path = os.environ.get("MODEL_PATH", "stock_prediction_model.keras")
    model = load_model(model_path)

    # Step 5: Make prediction
    prediction = model.predict(X_test)
    prediction = scaler.inverse_transform(prediction)

    # Step 6: Evaluation
    actual = df[60:].values
    mse = np.mean((prediction - actual) ** 2)
    rmse = np.sqrt(mse)
    r2 = 1 - (np.sum((prediction - actual) ** 2) / np.sum((actual - actual.mean()) ** 2))

    # Step 7: Save charts
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    media_dir = os.path.join(settings.MEDIA_ROOT)
    os.makedirs(media_dir, exist_ok=True)

    history_filename = f"history_{ticker}_{timestamp}.png"
    prediction_filename = f"prediction_{ticker}_{timestamp}.png"

    history_plot_path = os.path.join(media_dir, history_filename)
    prediction_plot_path = os.path.join(media_dir, prediction_filename)

    # Historical price chart
    plt.figure(figsize=(10, 4))
    df['Close'].plot(title=f"{ticker} Closing Price History")
    plt.savefig(history_plot_path)
    plt.close()

    # Prediction vs Actual chart
    plt.figure(figsize=(10, 4))
    plt.plot(actual, label='Actual', color='green')
    plt.plot(prediction, label='Predicted', color='purple')
    plt.title(f"{ticker} Prediction vs Actual")
    plt.legend()
    plt.savefig(prediction_plot_path)
    plt.close()

    # Step 8: Save to DB if user is provided
    prediction_obj = None
    if user:
        prediction_obj = Prediction.objects.create(
            user=user,
            ticker=ticker,
            predicted_price=float(prediction[-1]),
            chart_history=history_filename,
            chart_prediction=prediction_filename
        )

    # Step 9: Return result
    return {
        "next_day_price": float(prediction[-1]),
        "mse": float(mse),
        "rmse": float(rmse),
        "r2": float(r2),
        "chart_history": f"media/{history_filename}",
        "chart_prediction": f"media/{prediction_filename}",
        "prediction_obj": prediction_obj  # Can be None
    }
