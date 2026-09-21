from datetime import datetime, date, time, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import connection, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient
from users.models import User
from clients.models import ClientProfile
from services.models import Service
from .models import Appointment, BusinessHour, BlockedSlot, ScheduleSettings

TEST_PASSWORD = 'Only-for-tests!9385'

class ApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('admin@example.com', TEST_PASSWORD, is_staff=True)
        self.user = User.objects.create_user('alice@example.com', TEST_PASSWORD)
        self.other = User.objects.create_user('bob@example.com', TEST_PASSWORD)
        self.profile = ClientProfile.objects.create(user=self.user, full_name='Alice Teste', phone='11999990001')
        self.other_profile = ClientProfile.objects.create(user=self.other, full_name='Bob Teste', phone='11999990002')
        self.service = Service.objects.create(name='Serviço teste', category='Beleza', duration_minutes=60, price=90)
        self.day = timezone.localdate() + timedelta(days=4)
        for i in range(7):
            BusinessHour.objects.create(day_of_week=i, opening_time=time(9), closing_time=time(18), break_start=time(12), break_end=time(13))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.payload = {'service': self.service.pk, 'appointment_date': str(self.day), 'start_time': '09:00'}

    def create(self, **changes):
        return self.client.post('/api/appointments/', {**self.payload, **changes}, format='json')

    def test_end_time_price_and_identity_are_server_controlled(self):
        response = self.create(client=self.other_profile.pk, end_time='09:01', price='0', status='completed', admin_notes='forged')
        self.assertEqual(response.status_code, 201, response.data)
        obj = Appointment.objects.get()
        self.assertEqual(obj.client, self.profile)
        self.assertEqual(obj.end_time, time(10))
        self.assertEqual(obj.price, 90)
        self.assertEqual(obj.status, 'pending')
        self.assertEqual(obj.admin_notes, '')
        self.assertNotIn('admin_notes', response.data)

    def test_reject_overlap_and_interval(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(self.create(start_time='09:30').status_code, 400)
        self.assertEqual(self.create(start_time='10:00').status_code, 400)
        self.assertEqual(self.create(start_time='10:10').status_code, 201)

    def test_invalid_dates_hours_breaks_and_inactive_services(self):
        for changes in [{'appointment_date': str(timezone.localdate() - timedelta(days=1))}, {'start_time': '08:45'}, {'start_time': '17:30'}, {'start_time': '11:30'}, {'start_time': '09:00:15'}]:
            self.assertEqual(self.create(**changes).status_code, 400, changes)
        self.service.status = False
        self.service.save()
        self.assertEqual(self.create().status_code, 400)

    def test_closed_day_and_block(self):
        hour = BusinessHour.objects.get(day_of_week=self.day.weekday())
        hour.is_available = False
        hour.save()
        self.assertEqual(self.create().status_code, 400)
        hour.is_available = True
        hour.save()
        BlockedSlot.objects.create(date=self.day, start_time=time(9, 30), end_time=time(10, 30))
        self.assertEqual(self.create().status_code, 400)

    def test_slots_exclude_blocked_break_and_booked(self):
        self.create()
        BlockedSlot.objects.create(date=self.day, start_time=time(15), end_time=time(16))
        response = self.client.get('/api/available-slots/', {'date': self.day, 'service_id': self.service.pk})
        self.assertEqual(response.status_code, 200)
        values = [s['start_time'] for s in response.data['slots']]
        for value in ['09:00', '09:30', '10:00', '11:30', '12:00', '14:30', '15:00', '17:30']:
            self.assertNotIn(value, values)
        self.assertIn('10:15', values)
        self.assertIn('13:00', values)
        self.assertEqual(self.client.get('/api/available-slots/?date=no&service_id=no').status_code, 400)

    def test_object_ownership_and_staff_permissions(self):
        appointment_id = self.create().data['id']
        Appointment.objects.filter(pk=appointment_id).update(admin_notes='confidential')
        self.assertNotIn('admin_notes', self.client.get(f'/api/appointments/{appointment_id}/').data)
        self.assertEqual(self.client.get('/api/clients/').status_code, 403)
        self.assertEqual(self.client.post('/api/services/', {}).status_code, 403)
        self.assertEqual(self.client.post(f'/api/appointments/{appointment_id}/confirm/').status_code, 403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/appointments/').data, [])
        for method in ['get', 'delete']:
            self.assertEqual(getattr(self.client, method)(f'/api/appointments/{appointment_id}/').status_code, 404)

    def test_cancel_releases_slot_and_retains_history(self):
        pk = self.create().data['id']
        self.assertEqual(self.client.delete(f'/api/appointments/{pk}/').status_code, 200)
        self.assertEqual(Appointment.objects.get(pk=pk).status, 'cancelled')
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/cancel/').status_code, 400)

    def test_cancellation_deadline_and_admin_override(self):
        pk = self.create().data['id']
        ScheduleSettings.objects.filter(pk=1).update(cancellation_hours=240)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/cancel/').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/appointments/{pk}/', {'start_time': '14:00'}, format='json').status_code, 400)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/cancel/').status_code, 200)

    def test_state_transitions(self):
        pk = self.create().data['id']
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/complete/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/confirm/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/confirm/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/complete/').status_code, 400)
        Appointment.objects.filter(pk=pk).update(appointment_date=timezone.localdate() - timedelta(days=1))
        self.assertEqual(self.client.post(f'/api/appointments/{pk}/complete/').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/appointments/{pk}/', {'start_time': '13:00'}, format='json').status_code, 400)

    def test_rescheduling_conflicts_and_reconfirmation(self):
        pk = self.create().data['id']
        self.create(start_time='14:00')
        Appointment.objects.filter(pk=pk).update(status='confirmed')
        self.assertEqual(self.client.patch(f'/api/appointments/{pk}/', {'start_time': '14:30'}, format='json').status_code, 400)
        response = self.client.patch(f'/api/appointments/{pk}/', {'start_time': '10:15'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['end_time'], '11:15:00')

    def test_staff_create_edit_and_soft_delete(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post('/api/clients/', {'full_name': 'Nova cliente', 'email': 'NEW@example.com', 'phone': '(11) 99999-0003'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        c = ClientProfile.objects.get(pk=response.data['id'])
        self.assertEqual(c.user.email, 'new@example.com')
        self.assertFalse(c.user.has_usable_password())
        self.assertEqual(c.phone, '11999990003')
        self.assertEqual(self.client.delete(f'/api/clients/{c.pk}/').status_code, 204)
        c.refresh_from_db()
        self.assertFalse(c.status)
        self.assertFalse(User.objects.get(pk=c.user_id).is_active)
        self.assertEqual(self.client.delete(f'/api/services/{self.service.pk}/').status_code, 204)
        self.service.refresh_from_db()
        self.assertFalse(self.service.status)

    def test_hours_settings_and_block_validation(self):
        self.create()
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post('/api/blocked-slots/', {'date': str(self.day), 'start_time': '09:00', 'end_time': '11:00'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/blocked-slots/', {'date': str(self.day), 'start_time': '14:00', 'end_time': '15:00'}, format='json').status_code, 201)
        hour = BusinessHour.objects.first()
        for change in [{'opening_time': '20:00'}, {'break_start': '14:00'}, {'break_start': None}]:
            self.assertEqual(self.client.patch(f'/api/business-hours/{hour.pk}/', change, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/settings/', {'slot_step_minutes': 0}, format='json').status_code, 400)
        self.assertEqual(self.client.patch('/api/settings/', {'interval_minutes': 15}, format='json').status_code, 200)

    def test_registration_and_password_validation(self):
        self.client.force_authenticate(None)
        data = {'full_name': 'Cliente Nova', 'email': 'new@example.com', 'phone': '11977776666', 'password': TEST_PASSWORD, 'password_confirmation': TEST_PASSWORD, 'terms': True}
        self.assertEqual(self.client.post('/api/auth/register/', {**data, 'terms': False}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/auth/register/', {**data, 'password': '12345678', 'password_confirmation': '12345678'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/auth/register/', {**data, 'password_confirmation': 'wrong'}, format='json').status_code, 400)
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.get(email=data['email']).check_password(TEST_PASSWORD))
        self.assertTrue(ClientProfile.objects.get(user__email=data['email']).terms_accepted_at)
        self.assertEqual(self.client.post('/api/auth/register/', {**data, 'email': 'NEW@example.com'}, format='json').status_code, 400)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 403)

    def test_csrf_on_anonymous_auth_and_authenticated_mutations(self):
        client = APIClient(enforce_csrf_checks=True)
        login_data = {'email': self.user.email, 'password': TEST_PASSWORD}
        self.assertEqual(client.post('/api/auth/login/', login_data, format='json').status_code, 403)
        token = client.get('/api/auth/csrf/').data['csrfToken']
        response = client.post('/api/auth/login/', login_data, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(client.post('/api/appointments/', self.payload, format='json').status_code, 403)
        self.assertEqual(client.post('/api/appointments/', self.payload, format='json', HTTP_X_CSRFTOKEN=response.data['csrfToken']).status_code, 201)
        self.assertEqual(client.post('/api/auth/logout/').status_code, 403)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_reset_email_token_and_one_time_use(self):
        self.client.force_authenticate(None)
        a = self.client.post('/api/auth/password-reset/', {'email': self.user.email}, format='json')
        b = self.client.post('/api/auth/password-reset/', {'email': 'missing@example.com'}, format='json')
        self.assertEqual(a.data, b.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('#redefinir-senha?uid=', mail.outbox[0].body)
        data = {'uid': urlsafe_base64_encode(force_bytes(self.user.pk)), 'token': default_token_generator.make_token(self.user), 'password': 'New-password!7489', 'password_confirmation': 'New-password!7489'}
        self.assertEqual(self.client.post('/api/auth/password-reset-confirm/', data, format='json').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/password-reset-confirm/', data, format='json').status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(data['password']))

    def test_reserved_duration_and_price_survive_service_edit(self):
        pk = self.create().data['id']
        self.service.duration_minutes = 90
        self.service.price = 120
        self.service.save()
        self.client.force_authenticate(self.staff)
        response = self.client.post(f'/api/appointments/{pk}/confirm/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['duration_minutes'], 60)
        self.assertEqual(response.data['price'], '90.00')
        self.assertEqual(response.data['end_time'], '10:00:00')

    def test_deactivated_client_can_be_reactivated_by_staff(self):
        self.client.force_authenticate(self.staff)
        self.client.delete(f'/api/clients/{self.profile.pk}/')
        response = self.client.patch(f'/api/clients/{self.profile.pk}/', {'status': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_business_hours_default_times_are_valid(self):
        self.client.force_authenticate(self.staff)
        BusinessHour.objects.filter(day_of_week=0).delete()
        response = self.client.post('/api/business-hours/', {'day_of_week': 0}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['opening_time'], '09:00:00')

    def test_notifications_are_private(self):
        self.create()
        notifications = self.client.get('/api/notifications/').data
        self.assertEqual(len(notifications), 1)
        notification_id = notifications[0]['id']
        self.assertEqual(self.client.get(f'/api/notifications/{notification_id}/').status_code, 200)
        self.assertEqual(self.client.post('/api/notifications/read_all/').status_code, 200)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/notifications/').data, [])
        self.assertEqual(self.client.get(f'/api/notifications/{notification_id}/').status_code, 404)

@skipUnless(connection.vendor == 'mysql', 'Real row locking requires MySQL/InnoDB; executed in CI.')
class MySQLConcurrencyTests(TransactionTestCase):
    def test_two_simultaneous_requests_only_one_booking(self):
        ScheduleSettings.objects.get_or_create(pk=1)
        user = User.objects.create_user('concurrency@example.com', TEST_PASSWORD)
        ClientProfile.objects.create(user=user, full_name='Concorrência', phone='11999998888')
        service = Service.objects.create(name='Concorrência', category='Teste', duration_minutes=60, price=80)
        day = timezone.localdate() + timedelta(days=3)
        BusinessHour.objects.create(day_of_week=day.weekday(), opening_time=time(9), closing_time=time(18))
        barrier = Barrier(2)
        def request():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=user.pk))
                barrier.wait(timeout=10)
                return client.post('/api/appointments/', {'service': service.pk, 'appointment_date': str(day), 'start_time': '10:00'}, format='json').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: request(), range(2)))
        self.assertEqual(sorted(results), [201, 400])
        self.assertEqual(Appointment.objects.count(), 1)
