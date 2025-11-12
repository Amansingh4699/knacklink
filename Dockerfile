# -----------------------------
# ✅ KnackLink Django Deployment
# -----------------------------

# 1. Use official lightweight Python image
FROM python:3.12-slim

# 2. Set work directory in container
WORKDIR /app

# 3. Install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all project files
COPY . /app/

# 5. Move into Django project folder (where manage.py is)
WORKDIR /app/employee_dashboard

# 6. Collect static files
RUN python manage.py collectstatic --noinput

# 7. Expose port 8000 for Railway
EXPOSE 8000

# 8. Start the Django app using Gunicorn
CMD ["gunicorn", "employee_dashboard.wsgi:application", "--bind", "0.0.0.0:8000"]
