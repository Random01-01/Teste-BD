from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Service(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=80)
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(5), MaxValueValidator(480)])
    price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.URLField(blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
