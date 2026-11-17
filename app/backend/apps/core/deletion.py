"""Marcarea pentru ștergere (ca în 1C).

„Șterge” din liste și din documente doar **marchează** obiectul (`deletion_mark`): el rămâne în bază, se vede tăiat în
liste, nu se mai alege în câmpuri și nu se mai modifică până nu i se scoate marcajul. Ștergerea de tot o face
administratorul în *Administrare → Ștergerea obiectelor marcate*, și doar pentru obiectele pe care nu le folosește nimic
altceva din bază: o legătură PROTECT / RESTRICT, un câmp care s-ar goli (SET_NULL) sau un document / clasificator de sine
stătător care s-ar șterge odată cu el (de ex. foile de boală ale angajatului). Rândurile proprii ale obiectului (pozițiile
ordinului, actele din dosar) se șterg împreună cu el. Obiectele marcate și alese împreună se șterg în ordinea potrivită
(întâi ordinul-ciornă, apoi angajatul din el).

Un model devine marcabil cu câmpul `deletion_mark`; viewset-ul lui primește `DeletionMarkMixin`, iar verificările de
dinainte de ștergere (de ex. „ordinul semnat nu se șterge”) stau în `check_delete`.
"""
from functools import lru_cache

from django.apps import apps
from django.db import router, transaction
from django.db.models import ProtectedError, RestrictedError
from django.db.models.deletion import CASCADE, Collector
from rest_framework import permissions, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import require

FIELD = "deletion_mark"
MARKED_MESSAGE = "Obiectul este marcat pentru ștergere. Scoateți marcajul ca să-l puteți modifica."
MAX_REFS = 20


def is_markable(model) -> bool:
    return _markable(model._meta.concrete_model)


@lru_cache(maxsize=None)
def _markable(model) -> bool:
    return any(f.name == FIELD for f in model._meta.concrete_fields)


def markable_models() -> list:
    return [m for m in apps.get_models() if is_markable(m)]


_HOOKS: dict = {}


def on_mark(model):
    """Ce se mai face la marcare / la scoaterea marcajului unui model (de ex. absența foii de boală): `fn(obj, marked)`."""
    def wrap(fn):
        _HOOKS[model] = fn
        return fn
    return wrap


def set_mark(obj, marked: bool):
    if getattr(obj, FIELD) == marked:
        return
    with transaction.atomic():
        setattr(obj, FIELD, marked)
        obj.save(update_fields=[FIELD])
        hook = _HOOKS.get(type(obj))
        if hook:
            hook(obj, marked)


def ensure_not_marked(obj):
    """Documentul marcat nu se mai schimbă (nici rândurile lui)."""
    if getattr(obj, FIELD, False):
        raise ValidationError({"detail": MARKED_MESSAGE})


def key_of(obj) -> str:
    return f"{obj._meta.label}:{obj.pk}"


def from_key(key: str):
    try:
        label, pk = str(key).rsplit(":", 1)
        model = apps.get_model(label)
    except (ValueError, LookupError):
        return None
    if not is_markable(model):
        return None
    return model._base_manager.filter(pk=pk).first()


# --- legăturile -------------------------------------------------------------------------------------------------
def _owner(obj):
    """Obiectul de sine stătător al unui rând (poziția → ordinul, rândul → calculul), ca legătura să se poată găsi."""
    for field in obj._meta.concrete_fields:
        if field.is_relation and field.many_to_one and field.remote_field.on_delete is CASCADE \
                and is_markable(field.related_model):
            return getattr(obj, field.name, None)
    return None


def describe(obj) -> dict:
    owner = None if is_markable(type(obj)) else _owner(obj)
    shown = owner or obj
    return {"key": key_of(shown), "model": shown._meta.label, "type": str(shown._meta.verbose_name), "title": str(shown)[:200],
            "part": str(obj._meta.verbose_name) if owner else ""}


def _through_ref(row, obj):
    """Rândul unui many-to-many: legătura e a celuilalt obiect dacă relația e declarată la el (nu la `obj`)."""
    source = row._meta.auto_created
    if not source or isinstance(obj, source):
        return None
    for field in row._meta.concrete_fields:
        if field.is_relation and field.related_model is source:
            return getattr(row, field.name, None)
    return None


def references(obj) -> list:
    """Obiectele din bază care folosesc `obj` și s-ar strica la ștergerea lui (gol — se poate șterge)."""
    collector = Collector(using=router.db_for_write(type(obj)), origin=obj)
    try:
        collector.collect([obj])
    except ProtectedError as exc:
        return list(exc.protected_objects)[:MAX_REFS]
    except RestrictedError as exc:
        return list(exc.restricted_objects)[:MAX_REFS]
    deleted = {(type(x)._meta.concrete_model, x.pk) for _, x in collector.instances_with_model()}
    found = []

    def take(items):
        for item in items:
            if len(found) >= MAX_REFS:
                return
            if item._meta.auto_created:
                ref = _through_ref(item, obj)
                if ref is not None:
                    found.append(ref)
            elif is_markable(type(item)) and not (type(item) is type(obj) and item.pk == obj.pk):
                found.append(item)

    for _, instances in collector.data.items():
        take(instances)
    for qs in collector.fast_deletes:
        take(qs[:MAX_REFS] if hasattr(qs, "query") else qs)
    for _, groups in collector.field_updates.items():  # câmpurile care s-ar goli (SET_NULL / SET_DEFAULT)
        for group in groups:
            for item in (group[:MAX_REFS] if hasattr(group, "query") else group):
                if (type(item)._meta.concrete_model, item.pk) not in deleted and len(found) < MAX_REFS:
                    found.append(item)
    unique, seen = [], set()
    for item in found:
        if key_of(item) not in seen:
            seen.add(key_of(item))
            unique.append(item)
    return unique


def delete_marked(objs) -> tuple[list, list]:
    """Șterge obiectele marcate pe care nu le mai folosește nimic. Se reia cât timp se mai șterge ceva: obiectele alese
    împreună (ordinul-ciornă și angajatul din el) se șterg în ordinea potrivită. Întoarce (șterse, rămase cu legăturile)."""
    pending = [o for o in objs if getattr(o, FIELD, False)]
    deleted = []
    progress = True
    while pending and progress:
        progress = False
        for obj in list(pending):
            if references(obj):
                continue
            info = describe(obj)
            try:
                with transaction.atomic():
                    obj.delete()
            except (ProtectedError, RestrictedError):
                continue
            pending.remove(obj)
            deleted.append(info)
            progress = True
    blocked = [{**describe(o), "refs": [describe(r) for r in references(o)]} for o in pending]
    return deleted, blocked


# --- viewset-urile ----------------------------------------------------------------------------------------------
_SERIALIZERS: dict = {}


def with_mark(cls):
    """Serializatorul listei / formei cu `deletion_mark` (doar citire): rândul marcat se arată tăiat."""
    fields = getattr(getattr(cls, "Meta", None), "fields", None)
    if isinstance(fields, (list, tuple)) and FIELD in fields:  # pus de mână (serializatorii făcuți la fiecare cerere)
        return cls
    if cls not in _SERIALIZERS:
        attrs = {FIELD: serializers.BooleanField(read_only=True)}
        meta = getattr(cls, "Meta", None)
        fields = getattr(meta, "fields", None)
        if isinstance(fields, (list, tuple)) and FIELD not in fields:
            attrs["Meta"] = type("Meta", (meta,), {"fields": [*fields, FIELD]})
        _SERIALIZERS[cls] = type(cls.__name__, (cls,), attrs)
    return _SERIALIZERS[cls]


class DeletionMarkMixin:
    """„Șterge” (DELETE) marchează obiectul pentru ștergere; `POST …/unmark/` scoate marcajul (dreptul „șterge”).
    Obiectul marcat se deschide și se tipărește, dar nu se mai modifică."""

    def check_delete(self, instance):
        """Verificările de dinainte de marcare — aceleași ca la ștergerea de până acum."""

    def get_serializer(self, *args, **kwargs):  # nu get_serializer_class: multe view-uri și-l aleg singure
        kwargs.setdefault("context", self.get_serializer_context())
        return with_mark(self.get_serializer_class())(*args, **kwargs)

    def get_object(self):
        obj = super().get_object()
        if getattr(obj, FIELD, False) and self.request.method not in permissions.SAFE_METHODS \
                and self.action not in ("destroy", "unmark"):
            raise ValidationError({"detail": MARKED_MESSAGE})
        return obj

    def perform_destroy(self, instance):
        if getattr(instance, FIELD):
            return
        self.check_delete(instance)
        set_mark(instance, True)

    @action(detail=True, methods=["post"])
    def unmark(self, request, pk=None):
        obj = self.get_object()
        set_mark(obj, False)
        return Response(self.get_serializer(obj).data)


# --- Administrare → Ștergerea obiectelor marcate ----------------------------------------------------------------
def _keys(request) -> list:
    keys = request.data.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValidationError({"keys": "Alegeți obiectele."})
    return [o for o in (from_key(k) for k in keys[:2000]) if o is not None]


class MarkedView(APIView):
    """Lista tuturor obiectelor marcate pentru ștergere, pe tipuri."""

    def get(self, request):
        require(request.user, "settings.view")
        rows = []
        for model in markable_models():
            for obj in model._base_manager.filter(**{FIELD: True}).order_by("pk")[:1000]:
                rows.append(describe(obj))
        return Response(rows)


class MarkedCheckView(APIView):
    """Legăturile fiecărui obiect ales (fără ștergere)."""

    def post(self, request):
        require(request.user, "settings.view")
        return Response({key_of(o): [describe(r) for r in references(o)] for o in _keys(request)})


class MarkedDeleteView(APIView):
    def post(self, request):
        require(request.user, "settings.edit")
        deleted, blocked = delete_marked(_keys(request))
        return Response({"deleted": deleted, "blocked": blocked})


class MarkedUnmarkView(APIView):
    def post(self, request):
        require(request.user, "settings.edit")
        objs = [o for o in _keys(request) if getattr(o, FIELD)]
        for obj in objs:
            set_mark(obj, False)
        return Response({"unmarked": len(objs)})
