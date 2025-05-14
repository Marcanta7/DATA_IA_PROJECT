# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Make port 8080 available to the world outside this container
# Cloud Run will automatically set the PORT environment variable
# EXPOSE 8080 # Not strictly necessary for Cloud Run if PORT env var is used

# Define environment variable for the port
ENV PORT 8080

# Run main.py when the container launches
CMD ["python", "main.py"]