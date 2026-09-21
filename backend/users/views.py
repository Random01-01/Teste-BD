from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction, IntegrityError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from clients.serializers import ClientSerializer

User = get_user_model()

def user_data(user):
    return {'id': user.id, 'email': user.email, 'is_staff': user.is_staff,
            'name': user.profile.full_name if hasattr(user, 'profile') else user.first_name or 'Profissional',
            'profile': ClientSerializer(user.profile).data if hasattr(user, 'profile') else None}

@method_decorator(csrf_protect, name='dispatch')
class AuthView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

class CsrfView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'csrfToken': get_token(request)})

class RegisterView(AuthView):
    def post(self, request):
        serializer = ClientSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                profile = serializer.save()
        except IntegrityError:
            raise ValidationError('E-mail ou telefone já cadastrado.')
        login(request, profile.user)
        return Response({**user_data(profile.user), 'csrfToken': get_token(request)}, status=status.HTTP_201_CREATED)

class LoginView(AuthView):
    def post(self, request):
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError('Dados de login inválidos.')
        user = authenticate(request, email=email.strip().lower(), password=password)
        if not user:
            return Response({'detail': 'E-mail ou senha inválidos.'}, status=400)
        login(request, user)
        return Response({**user_data(user), 'csrfToken': get_token(request)})

class LogoutView(AuthView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        logout(request)
        return Response({'detail': 'Você saiu com segurança.', 'csrfToken': get_token(request)})

class MeView(APIView):
    def get(self, request):
        return Response(user_data(request.user))
    def patch(self, request):
        if not hasattr(request.user, 'profile'):
            raise ValidationError('Este usuário não possui perfil de cliente.')
        serializer = ClientSerializer(request.user.profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError('E-mail ou telefone já cadastrado.')
        return Response(user_data(request.user))

class PasswordResetView(AuthView):
    def post(self, request):
        email = serializers.EmailField().run_validation(request.data.get('email'))
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f'{settings.FRONTEND_URL.rstrip("/")}/#redefinir-senha?uid={uid}&token={token}'
            send_mail('Redefina sua senha • Aura', f'Para criar uma nova senha, acesse:\n{link}\nSe não solicitou, ignore este e-mail.', settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({'detail': 'Se o e-mail estiver cadastrado, você receberá as instruções.'})

class PasswordResetConfirmView(AuthView):
    def post(self, request):
        try:
            user = User.objects.get(pk=urlsafe_base64_decode(request.data.get('uid', '')).decode())
        except (ValueError, TypeError, UnicodeDecodeError, User.DoesNotExist):
            raise ValidationError('Link inválido ou expirado.')
        token = request.data.get('token', '')
        if not isinstance(token, str) or not default_token_generator.check_token(user, token):
            raise ValidationError('Link inválido ou expirado.')
        password = serializers.CharField().run_validation(request.data.get('password'))
        if password != request.data.get('password_confirmation'):
            raise ValidationError('As senhas não coincidem.')
        try:
            validate_password(password, user)
        except DjangoValidationError as exc:
            raise ValidationError({'password': exc.messages})
        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Senha atualizada. Você já pode entrar.'})


def csrf_failure(request, reason=''):
    from django.http import JsonResponse
    return JsonResponse({'detail': 'Sua sessão de segurança expirou. Atualize a página e tente novamente.'}, status=403)
