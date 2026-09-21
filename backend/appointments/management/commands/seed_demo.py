import os
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from users.models import User
from clients.models import ClientProfile
from services.models import Service
from appointments.models import BusinessHour, Appointment, ScheduleSettings, Notification

class Command(BaseCommand):
    help = 'Cria dados FICTÍCIOS para desenvolvimento. Exige DEBUG e DEMO_PASSWORD no ambiente.'
    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv('DEMO_PASSWORD')
        if not settings.DEBUG or not password:
            raise CommandError('Use somente com DEBUG=True e DEMO_PASSWORD definido no ambiente.')
        email = os.getenv('DEMO_EMAIL', 'demo@example.com')
        admin, _ = User.objects.get_or_create(email=email, defaults={'first_name': 'Mariana', 'is_staff': True})
        admin.set_password(password)
        admin.save()
        config = ScheduleSettings.objects.get(pk=1)
        config.professional_name = 'Mariana'
        config.save()
        for day in range(7):
            BusinessHour.objects.get_or_create(day_of_week=day, defaults={'opening_time': time(8), 'closing_time': time(19),
                'break_start': time(12), 'break_end': time(13), 'is_available': day != 6})
        specs = [
            ('Design de sobrancelhas', 'Sobrancelhas', 30, '45.00', 'Um design personalizado que valoriza a beleza natural do seu olhar.'),
            ('Manicure & pedicure', 'Unhas', 60, '85.00', 'Cuidado completo para suas mãos e pés, com acabamento impecável.'),
            ('Limpeza de pele', 'Estética facial', 60, '150.00', 'Renove sua pele com uma limpeza profunda e hidratação delicada.'),
            ('Extensão de cílios', 'Cílios', 90, '180.00', 'Leveza e volume na medida certa para realçar o seu olhar.'),
            ('Massagem relaxante', 'Bem-estar', 60, '120.00', 'Uma pausa para você. Alivie tensões e reencontre seu equilíbrio.'),
            ('Brow lamination', 'Sobrancelhas', 45, '110.00', 'Fios alinhados e um efeito naturalmente preenchido por mais tempo.'),
        ]
        services = []
        for name, category, duration, price, desc in specs:
            obj, _ = Service.objects.get_or_create(name=name, defaults={'category': category, 'duration_minutes': duration, 'price': price, 'description': desc})
            services.append(obj)
        names = ['Ana Clara Silva', 'Beatriz Oliveira', 'Camila Santos', 'Juliana Costa', 'Fernanda Lima', 'Isabela Martins', 'Letícia Souza', 'Mariana Rocha', 'Patrícia Alves', 'Sofia Ribeiro', 'Carolina Melo', 'Luiza Ferreira']
        clients = []
        for i, name in enumerate(names):
            user, created = User.objects.get_or_create(email=f'cliente{i+1}@example.com')
            if created:
                user.set_unusable_password()
                user.save()
            profile, _ = ClientProfile.objects.get_or_create(user=user, defaults={'full_name': name, 'phone': f'1199000{i:04}', 'terms_accepted_at': timezone.now()})
            clients.append(profile)
        today = timezone.localdate()
        # Idempotent within each day; historical rows are intentionally synthetic seed fixtures.
        for offset in range(-21, 8):
            day = today + timedelta(days=offset)
            if day.weekday() == 6: continue
            times = [(8, 0), (9, 0), (10, 30), (13, 0), (14, 45), (16, 30)]
            ids = [0, 1, 2, 3, 4, 5]
            for i, (hour, minute) in enumerate(times):
                service = services[ids[i]]
                starts = datetime.combine(day, time(hour, minute))
                ends = starts + timedelta(minutes=service.duration_minutes)
                state = 'completed' if ends < timezone.localtime().replace(tzinfo=None) else ('pending' if i in [2, 4] else 'confirmed')
                Appointment.objects.get_or_create(appointment_date=day, start_time=starts.time(), defaults={
                    'client': clients[(i + offset) % len(clients)], 'service': service, 'end_time': ends.time(), 'status': state, 'price': service.price})
        if not Notification.objects.filter(user=admin).exists():
            Notification.objects.create(user=admin, message='Bem-vinda ao Aura! Este ambiente contém apenas dados fictícios para você explorar.')
        self.stdout.write(self.style.SUCCESS('Demonstração criada. Nenhum dado real de cliente foi utilizado.'))
