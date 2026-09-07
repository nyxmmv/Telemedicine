from django.contrib.auth.models import User
from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=200)
    specialisation = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT)
    date = models.DateField()
    time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.username} - {self.doctor.name} - {self.date}"
