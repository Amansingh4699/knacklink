from django.db import models
from django.contrib.auth.models import User

class UserTime(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    day_of_week = models.CharField(max_length=10)
    start_time = models.TimeField()
    finish_time = models.TimeField()
    productive_hours = models.DecimalField(max_digits=4, decimal_places=2)
    target_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.00)
    comment = models.TextField(blank=True, null=True)

    def total_hours(self):
        from datetime import datetime, timedelta
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.finish_time)
        delta = end - start
        return round(delta.total_seconds() / 3600, 2)

    def __str__(self):
        return f"{self.user.username} - {self.date}"
