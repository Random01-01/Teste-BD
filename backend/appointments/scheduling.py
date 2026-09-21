from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import Appointment, BusinessHour, BlockedSlot, ScheduleSettings

ACTIVE = ['pending', 'confirmed', 'completed']

def lock_schedule():
    # Row is created in a data migration; do NOT get_or_create a mutex at runtime.
    return ScheduleSettings.objects.select_for_update().get(pk=1)

def local_datetime(day, at):
    return timezone.make_aware(datetime.combine(day, at))

def validate_slot(service, day, start, exclude=None, config=None, duration=None):
    config = config or ScheduleSettings.objects.get(pk=1)
    if not service.status:
        raise ValidationError('Este serviço está inativo.')
    begins = local_datetime(day, start)
    ends = begins + timedelta(minutes=duration or service.duration_minutes)
    if begins <= timezone.now():
        raise ValidationError('Escolha uma data e um horário futuros.')
    hour = BusinessHour.objects.filter(day_of_week=day.weekday(), is_available=True).first()
    if not hour or ends.date() != day or start < hour.opening_time or ends.time() > hour.closing_time:
        raise ValidationError('Horário fora do período de atendimento.')
    if start.second or start.microsecond:
        raise ValidationError('Selecione um horário sem segundos.')
    if hour.break_start and start < hour.break_end and ends.time() > hour.break_start:
        raise ValidationError('Este horário coincide com o intervalo de descanso.')
    if BlockedSlot.objects.filter(date=day, start_time__lt=ends.time(), end_time__gt=start).exists():
        raise ValidationError('Este horário está bloqueado.')
    gap = timedelta(minutes=config.interval_minutes)
    qs = Appointment.objects.filter(appointment_date=day, status__in=ACTIVE)
    if exclude:
        qs = qs.exclude(pk=exclude)
    for appointment in qs:
        if begins < local_datetime(day, appointment.end_time) + gap and ends + gap > local_datetime(day, appointment.start_time):
            raise ValidationError('Este horário acabou de ser ocupado. Escolha outro horário.')
    return ends.time()

def available_slots(service, day):
    hour = BusinessHour.objects.filter(day_of_week=day.weekday(), is_available=True).first()
    if not hour or not service.status or day < timezone.localdate():
        return []
    if day > timezone.localdate() + timedelta(days=366):
        raise ValidationError('Consulte datas nos próximos 12 meses.')
    config = ScheduleSettings.objects.get(pk=1)
    cursor = local_datetime(day, hour.opening_time)
    end = local_datetime(day, hour.closing_time)
    slots = []
    while cursor < end:
        try:
            final = validate_slot(service, day, cursor.time(), config=config)
            slots.append({'start_time': cursor.strftime('%H:%M'), 'end_time': final.strftime('%H:%M')})
        except ValidationError:
            pass
        cursor += timedelta(minutes=config.slot_step_minutes)
    return slots
