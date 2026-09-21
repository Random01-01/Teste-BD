from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import CsrfView, RegisterView, LoginView, LogoutView, MeView, PasswordResetView, PasswordResetConfirmView
from appointments.views import (ClientViewSet, ServiceViewSet, BusinessHourViewSet, BlockedSlotViewSet,
                                AppointmentViewSet, AvailableSlotsView, SettingsView, NotificationViewSet)
router = DefaultRouter()
for prefix, viewset, name in [
    ('clients', ClientViewSet, 'client'), ('services', ServiceViewSet, 'service'),
    ('business-hours', BusinessHourViewSet, 'business-hour'), ('blocked-slots', BlockedSlotViewSet, 'blocked-slot'),
    ('appointments', AppointmentViewSet, 'appointment'), ('notifications', NotificationViewSet, 'notification')]:
    router.register(prefix, viewset, basename=name)
urlpatterns = [
    path('admin/', admin.site.urls), path('api/', include(router.urls)),
    path('api/auth/csrf/', CsrfView.as_view()), path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()), path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/me/', MeView.as_view()), path('api/auth/password-reset/', PasswordResetView.as_view()),
    path('api/auth/password-reset-confirm/', PasswordResetConfirmView.as_view()),
    path('api/available-slots/', AvailableSlotsView.as_view()), path('api/settings/', SettingsView.as_view()),
]
