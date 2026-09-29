from datetime import datetime, date, time
from rest_framework import serializers
from .models import Appointment, BusinessHour, BlockedSlot, ScheduleSettings, Notification
from services.models import Service

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class BusinessHourSerializer(serializers.ModelSerializer):
    opening_time = serializers.TimeField(default=time(9))
    closing_time = serializers.TimeField(default=time(18))
    class Meta:
        model = BusinessHour
        fields = '__all__'
    def validate(self, attrs):
        def val(k): return attrs.get(k, getattr(self.instance, k, None))
        if val('opening_time') >= val('closing_time'):
            raise serializers.ValidationError('O fechamento deve ser após a abertura.')
        a, b = val('break_start'), val('break_end')
        if bool(a) != bool(b) or (a and not val('opening_time') <= a < b <= val('closing_time')):
            raise serializers.ValidationError('Intervalo inválido.')
        return attrs

class BlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedSlot
        fields = '__all__'
    def validate(self, attrs):
        start = attrs.get('start_time', getattr(self.instance, 'start_time', None))
        end = attrs.get('end_time', getattr(self.instance, 'end_time', None))
        if start >= end:
            raise serializers.ValidationError('O fim deve ser após o início.')
        return attrs

class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleSettings
        exclude = ['id']

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    category = serializers.CharField(source='service.category', read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    def get_duration_minutes(self, obj):
        return int((datetime.combine(obj.appointment_date, obj.end_time) - datetime.combine(obj.appointment_date, obj.start_time)).total_seconds() // 60)
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['end_time', 'price', 'status', 'created_at', 'updated_at']
        extra_kwargs = {'client': {'required': False}}
    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and not request.user.is_staff:
            fields.pop('admin_notes', None)
            fields['client'].read_only = True
        return fields

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'read', 'created_at']
        read_only_fields = ['message', 'created_at']
