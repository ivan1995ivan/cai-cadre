from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core import console
from apps.core.audit import set_current_user


class AuditedJWTAuthentication(JWTAuthentication):
    """Autentificare JWT care memorează utilizatorul curent pentru jurnalul de audit și pentru consola serverului.
    Sesiunea închisă din consolă nu mai e primită; cât intrarea în bază e blocată, intră doar administratorii."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, token = result
            if console.is_closed(console.session_id(token, user)):
                raise AuthenticationFailed("Sesiunea a fost închisă de administrator. Intrați din nou.", code="session_closed")
            if console.blocked() and not user.is_crm_admin:
                raise AuthenticationFailed(console.block_message(), code="maintenance")
            set_current_user(user)
            console.note_auth(user, token)
        return result


class SessionTokenSerializer(TokenObtainPairSerializer):
    """La intrare jetoanele primesc `sid` (sesiunea); îl păstrează și la reîmprospătare."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["sid"] = console.new_sid()
        return token


class SessionRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
        except Exception as exc:  # noqa: BLE001 — jetonul greșit îl respinge serializerul de bază
            raise InvalidToken(str(exc)) from exc
        sid = refresh.get("sid")
        if sid and console.is_closed(str(sid)):
            raise InvalidToken("Sesiunea a fost închisă de administrator.")
        return super().validate(attrs)
