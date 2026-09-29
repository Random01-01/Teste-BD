"""Consistent CSRF errors for Django's decorators and DRF session auth."""
from django.middleware.csrf import REASON_NO_CSRF_COOKIE
from rest_framework.authentication import SessionAuthentication, CSRFCheck
from rest_framework.exceptions import APIException


def csrf_error_payload(reason):
    if reason == REASON_NO_CSRF_COOKIE:
        category = 'cookie_missing'
    elif reason.startswith('Origin checking failed'):
        category = 'origin_rejected'
    elif reason.startswith('Referer checking failed'):
        category = 'referer_rejected'
    else:
        category = 'token_invalid'
    # Do not send raw middleware diagnostics (URLs, headers, etc.) to clients.
    return {
        'code': 'csrf_failed',
        'csrfReason': category,
        'detail': 'Não foi possível validar a segurança desta requisição.',
    }


class CsrfRejected(APIException):
    status_code = 403
    default_code = 'csrf_failed'

    def __init__(self, reason):
        super().__init__(detail=csrf_error_payload(reason))


class CsrfSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        # Same check as DRF's SessionAuthentication, with a machine-readable error.
        # Do not exempt authenticated writes or trust tokens without their cookie.
        check = CSRFCheck(lambda request: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise CsrfRejected(reason)
