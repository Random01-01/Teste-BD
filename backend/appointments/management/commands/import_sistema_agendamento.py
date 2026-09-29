"""Importa os dados do script ``Sistema-Agendamento*.sql`` para os modelos do site.

O script da branch B cria o banco ``sistema_agendamento`` com tabelas próprias
(profissional, cliente, servico, horario_disponivel, agendamento...). O site do
Aura usa os modelos Django e cria as tabelas via ``migrate``; por isso o .sql
não é aplicado direto no banco do site. Este comando lê apenas os INSERTs do
arquivo e converte cada linha para o modelo equivalente, em uma transação única.

Regras de segurança/produtividade:
- ``usuario.senha_hash`` é sempre ignorado (o exemplo do arquivo não é um hash
  Django válido). Usuários importados ficam com senha inutilizável; use
  ``manage.py changepassword`` ou ``createsuperuser`` para credenciais reais.
- Nada é atualizado/apagado: registros existentes são preservados.
- Agendamentos com conflito de horário (mesma regra do trigger do arquivo) são
  pulados com aviso.
"""
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from appointments.models import Appointment, BusinessHour, ScheduleSettings
from clients.models import ClientProfile
from services.models import Service
from users.models import User

DAY_MAP = {
    'segunda': 0, 'terca': 1, 'terça': 1, 'quarta': 2, 'quinta': 3,
    'sexta': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6,
}
STATUS_MAP = {
    'PENDENTE': Appointment.Status.PENDING, 'CONFIRMADO': Appointment.Status.CONFIRMED,
    'CONCLUIDO': Appointment.Status.COMPLETED, 'CANCELADO': Appointment.Status.CANCELLED,
    'RECUSADO': Appointment.Status.REJECTED,
}


def strip_comments(sql):
    return '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))


def split_rows(values_blob):
    rows, depth, in_string, current = [], 0, False, ''
    for ch in values_blob:
        if in_string:
            current += ch
            if ch == "'":
                in_string = False
            continue
        if ch == "'":
            in_string = True
            current += ch
        elif ch == '(':
            depth += 1
            if depth > 1:
                current += ch
        elif ch == ')':
            depth -= 1
            if depth == 0:
                rows.append(current)
                current = ''
            else:
                current += ch
        elif depth > 0:
            current += ch
    return rows


def parse_values(row):
    values, in_string, current = [], False, ''
    for ch in row + ',':
        if in_string:
            current += ch
            if ch == "'":
                in_string = False
            continue
        if ch == "'":
            in_string = True
            current += ch
        elif ch == ',':
            values.append(current.strip())
            current = ''
        else:
            current += ch
    return [parse_scalar(v) for v in values]


def parse_scalar(token):
    token = token.strip()
    if token.upper() == 'NULL':
        return None
    if len(token) >= 2 and token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    try:
        return int(token)
    except ValueError:
        try:
            return Decimal(token)
        except InvalidOperation:
            return token


def parse_inserts(sql):
    sql = strip_comments(sql)
    result = {}
    pattern = re.compile(r"INSERT\s+INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES\s*(.+?);", re.I | re.S)
    for match in pattern.finditer(sql):
        table, columns, blob = match.group(1), match.group(2), match.group(3)
        names = [c.strip() for c in columns.split(',')]
        rows = [dict(zip(names, parse_values(row))) for row in split_rows(blob)]
        result.setdefault(table, []).extend(rows)
    return result


class Command(BaseCommand):
    help = ('Importa os INSERTs do SQL Sistema-Agendamento para os modelos do site. '
            'Uso: manage.py import_sistema_agendamento arquivo.sql [--profissional ID]')

    def add_arguments(self, parser):
        parser.add_argument('arquivo', type=str, help='Caminho do arquivo .sql')
        parser.add_argument('--profissional', type=int, default=None,
                            help='id_profissional a importar quando o arquivo tiver vários (padrão: primeiro)')

    def handle(self, *args, **options):
        path = Path(options['arquivo'])
        if not path.is_file():
            raise CommandError(f'Arquivo não encontrado: {path}')
        try:
            data = parse_inserts(path.read_text(encoding='utf-8-sig'))
        except Exception as exc:
            raise CommandError(f'Não foi possível interpretar o SQL: {exc}')
        if not data.get('profissional'):
            raise CommandError('O arquivo não contém INSERT em "profissional". Confira se é o Sistema-Agendamento.sql.')
        self.warnings = []
        self.created = {'servicos': 0, 'clientes': 0, 'usuarios': 0, 'horarios': 0, 'agendamentos': 0}
        try:
            with transaction.atomic():
                self._import(data, options.get('profissional'))
        except Exception as exc:
            raise CommandError(f'Importação revertida por erro: {exc}')
        for warning in self.warnings[:20]:
            self.stdout.write(self.style.WARNING(f'AVISO: {warning}'))
        if len(self.warnings) > 20:
            self.stdout.write(self.style.WARNING(f'... e mais {len(self.warnings) - 20} avisos.'))
        self.stdout.write(self.style.SUCCESS(
            'Importação concluída: ' + ', '.join(f'{k}={v}' for k, v in self.created.items()) +
            '. Credenciais não foram importadas; use createsuperuser/changepassword.'))

    def _import(self, data, professional_id):
        # The .sql relies on AUTO_INCREMENT (INSERTs often omit the id) while later
        # tables reference explicit ids 1..n; emulate fresh-table numbering.
        primary_keys = {
            'profissional': 'id_profissional', 'categoria_servico': 'id_categoria',
            'usuario': 'id_usuario', 'cliente': 'id_cliente', 'servico': 'id_servico',
            'horario_disponivel': 'id_horario', 'agendamento': 'id_agendamento',
        }
        for table, key in primary_keys.items():
            for index, row in enumerate(data.get(table, []), start=1):
                row.setdefault(key, index)
        professionals = {row.get('id_profissional'): row for row in data['profissional']}
        prof_id = professional_id if professional_id is not None else next(iter(professionals))
        if prof_id not in professionals:
            raise CommandError(f'id_profissional {prof_id} não existe no arquivo. Disponíveis: {list(professionals)}')
        professional = professionals[prof_id]
        settings_row = ScheduleSettings.objects.get(pk=1)
        settings_row.professional_name = str(professional.get('nome') or settings_row.professional_name)
        settings_row.save(update_fields=['professional_name'])

        categories = {row['id_categoria']: row.get('nome', '') for row in data.get('categoria_servico', [])}

        for row in data.get('usuario', []):
            self._import_admin(row)
        clients = self._import_clients(data.get('cliente', []))
        services = self._import_services(data.get('servico', []), categories, prof_id)
        self._import_hours(data.get('horario_disponivel', []), prof_id)
        self._import_appointments(data.get('agendamento', []), prof_id, clients, services)

    def _import_admin(self, row):
        email = (row.get('email') or '').strip().lower()
        if not email:
            self.warnings.append(f'usuario sem e-mail ignorado: {row}')
            return
        user, created = User.objects.get_or_create(email=email, defaults={
            'first_name': (row.get('nome') or '')[:150], 'is_staff': True})
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
            self.created['usuarios'] += 1
        if row.get('senha_hash'):
            self.warnings.append(f'hash de senha de {email} ignorado (não é formato Django). '
                                 f'Use: python manage.py changepassword {email}')

    def _import_clients(self, rows):
        clients = {}
        for row in rows:
            old_id = row.get('id_cliente')
            email = (row.get('email') or '').strip().lower()
            if not email:
                self.warnings.append(f'cliente {row.get("nome")} sem e-mail ignorado (login exige e-mail).')
                continue
            user, user_created = User.objects.get_or_create(email=email)
            if user_created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
            try:
                profile, created = ClientProfile.objects.get_or_create(
                    user=user, defaults={'full_name': row.get('nome') or email,
                                         'phone': row.get('telefone') or '', 'notes': 'Importado do Sistema-Agendamento.'})
            except Exception as exc:
                self.warnings.append(f'cliente {row.get("nome")} ignorado ({exc}). Telefone deve ser único.')
                continue
            if created:
                self.created['clientes'] += 1
            clients[old_id] = profile
        return clients

    def _import_services(self, rows, categories, prof_id):
        services = {}
        for row in rows:
            old_id = row.get('id_servico')
            if row.get('id_profissional') not in (None, prof_id):
                self.warnings.append(f'serviço {row.get("nome")} de outro profissional ignorado (site com um profissional).')
                continue
            category = categories.get(row.get('id_categoria'), 'Geral')
            service, created = Service.objects.get_or_create(name=row.get('nome') or f'servico-{old_id}', defaults={
                'description': row.get('descricao') or '', 'category': category,
                'duration_minutes': int(row.get('duracao_minutos') or 60),
                'price': Decimal(row.get('preco') or 0), 'status': bool(row.get('ativo', True))})
            if created:
                self.created['servicos'] += 1
            services[old_id] = service
        return services

    def _import_hours(self, rows, prof_id):
        pending = {}
        for row in rows:
            if row.get('id_profissional') not in (None, prof_id):
                continue
            day = DAY_MAP.get(str(row.get('dia_semana', '')).strip().lower())
            if day is None:
                self.warnings.append(f'dia_semana desconhecido ignorado: {row.get("dia_semana")}')
                continue
            start, end = str(row.get('hora_inicio') or '')[:5], str(row.get('hora_fim') or '')[:5]
            if day not in pending:
                pending[day] = [start, end]
            else:
                pending[day] = [min(pending[day][0], start), max(pending[day][1], end)]
                self.warnings.append(f'vários intervalos no dia {day} combinados em um único horário de funcionamento.')
        for day, (start, end) in sorted(pending.items()):
            _, created = BusinessHour.objects.get_or_create(day_of_week=day, defaults={
                'opening_time': start, 'closing_time': end, 'is_available': True})
            if created:
                self.created['horarios'] += 1
            else:
                self.warnings.append(f'horário do dia {day} já existia no site; mantido o atual.')

    def _import_appointments(self, rows, prof_id, clients, services):
        for row in rows:
            if row.get('id_profissional') not in (None, prof_id):
                self.warnings.append(f'agendamento {row.get("id_agendamento")} de outro profissional ignorado.')
                continue
            client, service = clients.get(row.get('id_cliente')), services.get(row.get('id_servico'))
            if not client or not service:
                self.warnings.append(f'agendamento {row.get("id_agendamento")} ignorado: cliente ou serviço não importado.')
                continue
            status = STATUS_MAP.get(str(row.get('status') or 'CONFIRMADO').upper())
            if status is None:
                self.warnings.append(f'agendamento {row.get("id_agendamento")} ignorado: status {row.get("status")}.')
                continue
            day, start, end = str(row.get('data_agendamento')), str(row.get('hora_inicio'))[:5], str(row.get('hora_fim'))[:5]
            key = {'appointment_date': day, 'start_time': start, 'client': client, 'service': service}
            if Appointment.objects.filter(**key).exists():
                continue
            if status != Appointment.Status.CANCELLED and self._has_conflict(day, start, end):
                self.warnings.append(f'agendamento {row.get("id_agendamento")} ignorado: conflito de horário (regra do trigger).')
                continue
            notes = row.get('observacao') or ''
            admin_notes = ''
            if row.get('motivo_cancelamento'):
                admin_notes = f'Cancelamento: {row["motivo_cancelamento"]}'
                if row.get('data_cancelamento'):
                    admin_notes += f' em {row["data_cancelamento"]}'
            Appointment.objects.create(status=status, end_time=end, price=service.price,
                                      client_notes=notes, admin_notes=admin_notes, **key)
            self.created['agendamentos'] += 1

    def _has_conflict(self, day, start, end):
        return Appointment.objects.filter(appointment_date=day).exclude(
            status=Appointment.Status.CANCELLED).filter(
            start_time__lt=end, end_time__gt=start).exists()
