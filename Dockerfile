# Use an official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Collect static files (for Tailwind etc.)
RUN python manage.py collectstatic --noinput

# Run Gunicorn server
CMD gunicorn stock_prediction_main.wsgi:application --bind 0.0.0.0:8000 --workers 3
