from datetime import date, timedelta
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import BasePermission, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from clients.models import ClientProfile
from clients.serializers import ClientSerializer
from services.models import Service
from .models import Appointment, BusinessHour, BlockedSlot, ScheduleSettings, Notification
from .serializers import (ServiceSerializer, BusinessHourSerializer, BlockedSlotSerializer,
                          SettingsSerializer, AppointmentSerializer, NotificationSerializer)
from .scheduling import lock_schedule, validate_slot, available_slots, local_datetime, ACTIVE

class StaffOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ('GET', 'HEAD', 'OPTIONS') or request.user.is_staff

class LockedWrites:
    def perform_create(self, serializer):
        with transaction.atomic():
            lock_schedule()
            serializer.save()
    def perform_update(self, serializer):
        with transaction.atomic():
            lock_schedule()
            serializer.save()
    def perform_destroy(self, instance):
        with transaction.atomic():
            lock_schedule()
            instance.delete()

class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ClientSerializer
    queryset = ClientProfile.objects.select_related('user').all()
    def perform_create(self, serializer):
        try:
            with transaction.atomic(): serializer.save()
        except IntegrityError:
            raise ValidationError('E-mail ou telefone já cadastrado.')
    def perform_update(self, serializer):
        try:
            with transaction.atomic(): serializer.save()
        except IntegrityError:
            raise ValidationError('E-mail ou telefone já cadastrado.')
    def perform_destroy(self, instance):
        # Retain history, disable access instead of deleting personal appointment records.
        with transaction.atomic():
            instance.status = False
            instance.save()
            instance.user.is_active = False
            instance.user.save()
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        appointments = self.get_object().appointments.select_related('client', 'service').all()
        return Response(AppointmentSerializer(appointments, many=True, context={'request': request}).data)

class ServiceViewSet(LockedWrites, viewsets.ModelViewSet):
    permission_classes = [StaffOrReadOnly]
    serializer_class = ServiceSerializer
    def get_queryset(self):
        qs = Service.objects.all()
        return qs if self.request.user.is_staff else qs.filter(status=True)
    def perform_destroy(self, instance):
        with transaction.atomic():
            lock_schedule()
            instance.status = False
            instance.save(update_fields=['status'])

class BusinessHourViewSet(LockedWrites, viewsets.ModelViewSet):
    permission_classes = [StaffOrReadOnly]
    serializer_class = BusinessHourSerializer
    queryset = BusinessHour.objects.all()

class BlockedSlotViewSet(LockedWrites, viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = BlockedSlotSerializer
    queryset = BlockedSlot.objects.all()
    def save_block(self, serializer):
        with transaction.atomic():
            lock_schedule()
            data = {k: serializer.validated_data.get(k, getattr(serializer.instance, k, None)) for k in ['date', 'start_time', 'end_time']}
            if Appointment.objects.filter(appointment_date=data['date'], status__in=['pending', 'confirmed'],
                                          start_time__lt=data['end_time'], end_time__gt=data['start_time']).exists():
                raise ValidationError('Cancele ou reagende os atendimentos neste período antes de bloqueá-lo.')
            serializer.save()
    perform_create = save_block
    perform_update = save_block

class SettingsView(APIView):
    permission_classes = [StaffOrReadOnly]
    def get(self, request):
        return Response(SettingsSerializer(ScheduleSettings.objects.get(pk=1)).data)
    def patch(self, request):
        with transaction.atomic():
            config = lock_schedule()
            serializer = SettingsSerializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

class AvailableSlotsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        try:
            day = date.fromisoformat(request.query_params.get('date', ''))
            service_id = int(request.query_params.get('service_id', ''))
        except (ValueError, TypeError):
            raise ValidationError('Informe date (AAAA-MM-DD) e service_id válidos.')
        service = get_object_or_404(Service, pk=service_id, status=True)
        return Response({'date': day, 'slots': available_slots(service, day)})

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    def get_queryset(self):
        qs = Appointment.objects.select_related('client', 'service')
        if not self.request.user.is_staff:
            qs = qs.filter(client__user=self.request.user)
        for field in ['appointment_date', 'status', 'client']:
            value = self.request.query_params.get(field)
            if value:
                try:
                    if field == 'appointment_date': value = date.fromisoformat(value)
                    if field == 'client': value = int(value)
                except ValueError:
                    raise ValidationError(f'Filtro {field} inválido.')
                qs = qs.filter(**{field: value})
        return qs

    def perform_create(self, serializer):
        with transaction.atomic():
            config = lock_schedule()
            client = serializer.validated_data.get('client') if self.request.user.is_staff else getattr(self.request.user, 'profile', None)
            if not client or not client.status or not client.user.is_active:
                raise ValidationError('Selecione um cliente ativo.')
            service = Service.objects.get(pk=serializer.validated_data['service'].pk)
            end = validate_slot(service, serializer.validated_data['appointment_date'], serializer.validated_data['start_time'], config=config)
            obj = serializer.save(client=client, service=service, end_time=end, price=service.price)
            Notification.objects.create(user=client.user, message=f'Agendamento de {service.name} recebido para {obj.appointment_date:%d/%m}, às {obj.start_time:%H:%M}.')
            from users.models import User
            Notification.objects.bulk_create([
                Notification(user=professional, message=f'{client.full_name} solicitou {service.name} em {obj.appointment_date:%d/%m}, às {obj.start_time:%H:%M}.')
                for professional in User.objects.filter(is_staff=True, is_active=True).exclude(pk=client.user_id)
            ])

    def check_cancellation(self, appointment, config):
        if not self.request.user.is_staff and local_datetime(appointment.appointment_date, appointment.start_time) - timezone.now() < timedelta(hours=config.cancellation_hours):
            raise ValidationError(f'Alterações são permitidas com pelo menos {config.cancellation_hours} horas de antecedência. Entre em contato com o studio.')

    def perform_update(self, serializer):
        with transaction.atomic():
            config = lock_schedule()
            obj = Appointment.objects.select_for_update().get(pk=serializer.instance.pk)
            if obj.status not in ['pending', 'confirmed']:
                raise ValidationError('Este agendamento já foi finalizado.')
            self.check_cancellation(obj, config)
            data = serializer.validated_data
            service = Service.objects.get(pk=data.get('service', obj.service).pk)
            day, start = data.get('appointment_date', obj.appointment_date), data.get('start_time', obj.start_time)
            end = validate_slot(service, day, start, exclude=obj.pk, config=config)
            client = data.get('client', obj.client)
            if not client.status or not client.user.is_active:
                raise ValidationError('Selecione um cliente ativo.')
            serializer.instance = obj
            serializer.save(end_time=end, price=service.price if service.pk != obj.service_id else obj.price,
                            status='pending')
            Notification.objects.create(user=client.user, message=f'Agendamento de {service.name} reagendado para {day:%d/%m}, às {start:%H:%M}. Aguarde a confirmação.')

    def transition(self, target):
        with transaction.atomic():
            config = lock_schedule()
            obj = self.get_object()
            if not self.request.user.is_staff and target != 'cancelled':
                raise PermissionDenied('Apenas a profissional pode realizar esta ação.')
            allowed = {'confirmed': ['pending'], 'completed': ['confirmed'], 'cancelled': ['pending', 'confirmed'], 'rejected': ['pending']}
            if obj.status not in allowed[target]:
                raise ValidationError('Esta alteração de status não é permitida.')
            if target == 'cancelled': self.check_cancellation(obj, config)
            if target == 'confirmed':
                validate_slot(obj.service, obj.appointment_date, obj.start_time, exclude=obj.pk, config=config,
                              duration=int((local_datetime(obj.appointment_date, obj.end_time) - local_datetime(obj.appointment_date, obj.start_time)).total_seconds() // 60))
            if target == 'completed' and local_datetime(obj.appointment_date, obj.end_time) > timezone.now():
                raise ValidationError('Aguarde o término do atendimento para concluí-lo.')
            obj.status = target
            obj.save(update_fields=['status', 'updated_at'])
            Notification.objects.create(user=obj.client.user, message=f'Seu agendamento de {obj.service.name} foi {obj.get_status_display().lower()}.')
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None): return self.transition('cancelled')
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def confirm(self, request, pk=None): return self.transition('confirmed')
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None): return self.transition('completed')
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reject(self, request, pk=None): return self.transition('rejected')
    def destroy(self, request, *args, **kwargs):
        return self.transition('cancelled')

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    def list(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_queryset()[:100], many=True).data)
    @action(detail=False, methods=['post'])
    def read_all(self, request):
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({'detail': 'Notificações marcadas como lidas.'})
