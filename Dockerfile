# Use lightweight Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080 for web server
EXPOSE 8080

# Start the application
CMD ["python3", "main.py"]
