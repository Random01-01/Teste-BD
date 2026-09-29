from django.contrib import admin
from .models import Appointment, BusinessHour, BlockedSlot, ScheduleSettings, Notification

class ReadOnlyScheduleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None): return False
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

for model in [Appointment, BusinessHour, BlockedSlot, ScheduleSettings]:
    admin.site.register(model, ReadOnlyScheduleAdmin)
admin.site.register(Notification)
