FROM python:3.11-slim-bookworm

WORKDIR /app

# Install the requirement
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app script
COPY app.py .

# Streamlit network port
EXPOSE 8501

# Run the web server
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]