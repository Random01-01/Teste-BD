import re
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import ClientProfile

User = get_user_model()

class ClientSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    password = serializers.CharField(write_only=True, required=False)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    terms = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = ClientProfile
        fields = ['id', 'full_name', 'email', 'password', 'password_confirmation', 'terms', 'cpf',
                  'birth_date', 'phone', 'address', 'notes', 'status', 'created_at']
        read_only_fields = ['created_at']

    def validate_phone(self, value):
        phone = re.sub(r'\D', '', value)
        if not 10 <= len(phone) <= 13:
            raise serializers.ValidationError('Informe um telefone válido com DDD.')
        qs = ClientProfile.objects.filter(phone=phone)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este telefone já está cadastrado.')
        return phone

    def validate_cpf(self, value):
        digits = re.sub(r'\D', '', value)
        if not digits:
            return ''
        if len(digits) != 11 or len(set(digits)) == 1:
            raise serializers.ValidationError('CPF inválido.')
        for size in (9, 10):
            check = (sum(int(digits[i]) * (size + 1 - i) for i in range(size)) * 10 % 11) % 10
            if check != int(digits[size]):
                raise serializers.ValidationError('CPF inválido.')
        return digits

    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError('A data de nascimento não pode estar no futuro.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        staff = request and request.user.is_staff
        email = attrs.get('user', {}).get('email', '').lower().strip()
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance:
                qs = qs.exclude(pk=self.instance.user_id)
            if qs.exists():
                raise serializers.ValidationError({'email': 'Este e-mail já está cadastrado.'})
            attrs['user']['email'] = email
        if not staff:
            attrs.pop('status', None)
        if not self.instance and not staff:
            if not attrs.get('terms'):
                raise serializers.ValidationError({'terms': 'É necessário aceitar os termos de uso.'})
            if not attrs.get('password'):
                raise serializers.ValidationError({'password': 'Informe uma senha.'})
        password = attrs.get('password')
        if password:
            if password != attrs.get('password_confirmation'):
                raise serializers.ValidationError({'password_confirmation': 'As senhas não coincidem.'})
            try:
                validate_password(password, User(email=email, first_name=attrs.get('full_name', '')))
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': exc.messages})
        return attrs

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirmation', None)
        terms = validated_data.pop('terms', False)
        user = User.objects.create_user(password=password, **user_data)
        return ClientProfile.objects.create(user=user, terms_accepted_at=timezone.now() if terms else None, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirmation', None)
        validated_data.pop('terms', None)
        if password:
            instance.user.set_password(password)
        if 'email' in user_data:
            instance.user.email = user_data['email']
        if 'status' in validated_data:
            instance.user.is_active = validated_data['status']
        instance.user.save()
        return super().update(instance, validated_data)
