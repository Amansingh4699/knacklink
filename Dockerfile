# Use official Python image
FROM python:3.12-slim

# Set working directory in container
WORKDIR /app

# Copy only requirements first (for Docker caching)
COPY ../requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY .. /app/

# Set workdir to where manage.py actually exists
WORKDIR /app/employee_dashboard

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run Django app using Gunicorn
CMD ["gunicorn", "employee_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
