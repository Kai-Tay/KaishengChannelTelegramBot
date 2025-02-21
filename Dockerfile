# Use an official Python runtime as base image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy all necessary files
COPY requirements.txt .
COPY bot.py .
COPY .env .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables from .env file
ENV $(cat .env | xargs)

# Run the bot
CMD ["python", "bot.py"]

