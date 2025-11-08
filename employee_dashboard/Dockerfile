# Dockerfile
FROM python:3.10-slim

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    pip install --upgrade pip

# Copy and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy Django project files
COPY . .

# Expose port
EXPOSE 8000

# Run Gunicorn server
CMD ["gunicorn", "employee_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
