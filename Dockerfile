# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables to prevent Python from writing .pyc files and to buffer output
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies that might be required by some Python packages.
# This is a good practice for creating robust images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container first.
# This leverages Docker's layer caching. The dependencies will only be re-installed
# if the requirements.txt file changes.
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project directory into the container's working directory.
COPY . .

# Expose the port that Streamlit runs on.
EXPOSE 8501

# Healthcheck to ensure the Streamlit app is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Define the command to run the app.
# This command assumes the directory '4_app' has been renamed to 'app'.
# Using 0.0.0.0 makes the app accessible from outside the container.
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
