from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class ScheduleSettings(models.Model):
    """Singleton row is also the MySQL scheduling mutex. Always lock before writes."""
    studio_name = models.CharField(max_length=100, default='Studio Aura')
    professional_name = models.CharField(max_length=100, default='Mariana')
    interval_minutes = models.PositiveIntegerField(default=10, validators=[MaxValueValidator(120)])
    cancellation_hours = models.PositiveIntegerField(default=24, validators=[MaxValueValidator(720)])
    slot_step_minutes = models.PositiveIntegerField(default=15, validators=[MinValueValidator(5), MaxValueValidator(60)])

class BusinessHour(models.Model):
    day_of_week = models.PositiveSmallIntegerField(unique=True, validators=[MaxValueValidator(6)])
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='18:00')
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week']

class BlockedSlot(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']

class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        CONFIRMED = 'confirmed', 'Confirmado'
        COMPLETED = 'completed', 'Concluído'
        CANCELLED = 'cancelled', 'Cancelado'
        REJECTED = 'rejected', 'Recusado'
    client = models.ForeignKey('clients.ClientProfile', on_delete=models.PROTECT, related_name='appointments')
    service = models.ForeignKey('services.Service', on_delete=models.PROTECT, related_name='appointments')
    appointment_date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    price = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    client_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'start_time']
        indexes = [models.Index(fields=['appointment_date', 'status'])]
        constraints = [models.CheckConstraint(condition=models.Q(end_time__gt=models.F('start_time')), name='appointment_positive_duration')]

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
