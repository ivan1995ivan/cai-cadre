"""Jurnalul de audit: cine, ce, când a modificat (valoarea veche → valoarea nouă).

Un model se înregistrează cu `register(Model)` (în AppConfig.ready). Pentru el se scriu automat
crearea, modificarea (doar câmpurile schimbate), ștergerea și schimbările relațiilor many-to-many.
Utilizatorul și IP-ul vin din contextul cererii curente.

Fiecare creare / modificare păstrează și starea completă (`snapshot`): e versiunea la care administratorul poate reveni
(istoricul din documente și fișe). Rândurile documentelor se înregistrează cu `parent="invoice"` etc., ca schimbările
pozițiilor să apară în istoricul documentului; `describe` dă textul rândului (de ex. „Șurub × 10”).
"""
import contextvars
import datetime
import decimal
import uuid

from django.db import models
from django.db.models.fields.files import FieldFile
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save

_current_user = contextvars.ContextVar("crm_current_user", default=None)
_current_ip = contextvars.ContextVar("crm_current_ip", default=None)

_REGISTRY: dict = {}


def set_current_user(user):
    _current_user.set(user)


def get_current_user():
    return _current_user.get()


def get_current_ip():
    return _current_ip.get()


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_token = _current_user.set(None)
        ip_token = _current_ip.set(client_ip(request))
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(user_token)
            _current_ip.reset(ip_token)


def _serialize(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, models.Model):
        return value.pk
    if isinstance(value, FieldFile):
        return value.name or None
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _snapshot(instance, exclude) -> dict:
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in exclude:
            continue
        data[field.name] = _serialize(getattr(instance, field.attname))
    return data


def _describe(instance):
    spec = _OPTIONS.get(type(instance), {})
    try:
        return str(spec["describe"](instance) if spec.get("describe") else instance)[:200]
    except Exception:  # noqa: BLE001 – descrierea nu trebuie să oprească salvarea
        return str(instance.pk)


def _parent(instance):
    spec = _OPTIONS.get(type(instance), {})
    field = spec.get("parent")
    if not field:
        return "", ""
    parent_id = getattr(instance, f"{field}_id", None)
    related = type(instance)._meta.get_field(field).related_model
    return (related._meta.label, str(parent_id)) if parent_id else ("", "")


def write(action: str, instance=None, changes=None, *, model_label="", object_id="", object_repr="", user=None,
          snapshot=None):
    from .models import AuditLog

    user = user or get_current_user()
    parent_model = parent_id = ""
    if instance is not None:
        model_label = instance._meta.label
        object_id = str(instance.pk)
        object_repr = _describe(instance)
        parent_model, parent_id = _parent(instance)
    AuditLog.objects.create(
        user=user if getattr(user, "pk", None) else None,
        username=getattr(user, "username", "") or "",
        action=action,
        model=model_label,
        object_id=object_id,
        object_repr=object_repr,
        changes=changes or {},
        snapshot=snapshot,
        parent_model=parent_model,
        parent_id=parent_id,
        ip=get_current_ip() or None,
    )


def _pre_save(sender, instance, **kwargs):
    if instance.pk is None:
        instance._audit_old = None
        return
    try:
        old = sender._default_manager.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_old = None
        return
    instance._audit_old = _snapshot(old, _REGISTRY[sender])


def _post_save(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    exclude = _REGISTRY[sender]
    new = _snapshot(instance, exclude)
    old = getattr(instance, "_audit_old", None)
    if created or old is None:
        write("create", instance, {k: [None, v] for k, v in new.items() if v not in (None, "", [], {})}, snapshot=new)
        return
    diff = {k: [old.get(k), v] for k, v in new.items() if old.get(k) != v}
    if diff:
        restored = getattr(instance, "_audit_restored_from", None)
        if restored:
            diff["_restored_from"] = restored
        write("update", instance, diff, snapshot=new)


def _post_delete(sender, instance, **kwargs):
    write("delete", instance, {k: [v, None] for k, v in _snapshot(instance, _REGISTRY[sender]).items()})


def _m2m_changed(sender, instance, action, model, pk_set, **kwargs):
    if type(instance) not in _REGISTRY or action not in ("post_add", "post_remove", "post_clear"):
        return
    field = next(
        (f.name for f in type(instance)._meta.many_to_many if f.remote_field.through is sender), "relații"
    )
    names = [str(o) for o in model._default_manager.filter(pk__in=pk_set or [])]
    verb = {"post_add": "adăugat", "post_remove": "eliminat", "post_clear": "golit"}[action]
    write("update", instance, {field: {verb: names}})


_OPTIONS: dict = {}


def line_label(line):
    """Textul unui rând de document în istoric: „Șurub × 7”."""
    qty = decimal.Decimal(str(line.qty or 0)).normalize()
    return f"{line.variant} × {qty:f}"


def create_many(model, objs):
    """bulk_create cu rândurile în jurnal. Unde baza nu întoarce id-urile de la bulk_create (SQL Server), rândurile se
    salvează pe rând — altfel n-ar avea id și n-ar apărea în istoric; save() le scrie singur în jurnal."""
    from django.db import connections, router

    objs = list(objs)
    if connections[router.db_for_write(model)].features.can_return_rows_from_bulk_insert:
        created = model.objects.bulk_create(objs)
        created_many(created)
        return created
    for obj in objs:
        obj.save(force_insert=True)
    return objs


def created_many(objs):
    """Rândurile create cu bulk_create (fără semnale) se scriu și ele în jurnal."""
    for obj in objs:
        if type(obj) in _REGISTRY and obj.pk:
            new = _snapshot(obj, _REGISTRY[type(obj)])
            write("create", obj, {k: [None, v] for k, v in new.items() if v not in (None, "", [], {})}, snapshot=new)


def register(model, exclude=None, *, parent=None, describe=None):
    _REGISTRY[model] = set(exclude or ()) | {"id"}
    _OPTIONS[model] = {"parent": parent, "describe": describe}
    pre_save.connect(_pre_save, sender=model, dispatch_uid=f"audit_pre_{model._meta.label}")
    post_save.connect(_post_save, sender=model, dispatch_uid=f"audit_post_{model._meta.label}")
    post_delete.connect(_post_delete, sender=model, dispatch_uid=f"audit_del_{model._meta.label}")
    for field in model._meta.many_to_many:
        m2m_changed.connect(
            _m2m_changed, sender=field.remote_field.through, dispatch_uid=f"audit_m2m_{model._meta.label}_{field.name}"
        )
