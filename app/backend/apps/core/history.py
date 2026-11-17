"""Istoricul modificărilor unui document / clasificator și revenirea la o versiune (doar administratorul).

Istoricul vine din jurnalul de audit: modificările obiectului și ale rândurilor lui (pozițiile documentului), cu
utilizatorul, data și câmpurile schimbate (valoarea veche → cea nouă, cu denumirile câmpurilor și ale obiectelor legate).
Revenirea pune înapoi câmpurile din versiunea aleasă; se poate doar la clasificatoare și la documentele-ciornă (cele
înregistrate se anulează întâi, ca stocul și datoriile să rămână corecte) și nu în perioada închisă.
"""
from django.apps import apps
from django.db import transaction
from django.db.models import Q

from .audit import _REGISTRY
from .models import AuditLog

# modelul → dreptul de vizualizare (istoricul îl vede cine vede obiectul)
VIEW_PERMS = {
    "billing.invoice": "invoices.view", "billing.deliverynote": "invoices.view", "billing.clientreturn": "invoices.view",
    "billing.payment": "payments.view", "orders.order": "orders.view", "sales.offer": "offers.view",
    "clients.client": "clients.view", "clients.clientsite": "clients.view", "clients.contactperson": "clients.view",
    "finance.contract": "payments.view", "finance.supplierpayment": "payments.view",
    "finance.serviceinvoice": "payments.view", "finance.serviceinvoiceline": "payments.view",
}


class HistoryError(ValueError):
    pass


def _model(label):
    try:
        model = apps.get_model(label)
    except (LookupError, ValueError) as exc:
        raise HistoryError("Tip de obiect necunoscut.") from exc
    if model not in _REGISTRY:
        raise HistoryError("Pentru acest tip de obiect nu se ține istoricul.")
    return model


APP_PERMS = {"catalog": "catalog.view", "inventory": "inventory.view", "logistics": "logistics.view",
             "production": "production.view", "wms": "wms.view", "printing": "settings.view", "core": "settings.view",
             "users": "users.view", "calculator": "offers.view", "sales": "prices.view", "shop": "shop.view",
             # CAI CADRE: istoricul dosarului arată și valorile vechi (IDNP, salariu) — doar cu dreptul „date sensibile”
             "staff": "employees.sensitive", "org": "org.view"}


def _check_view(user, model):
    perm = VIEW_PERMS.get(model._meta.label_lower) or APP_PERMS.get(model._meta.app_label)
    if perm and not user.is_crm_admin and not user.has_crm_perm(perm):
        raise HistoryError("Nu aveți acces la acest obiect.")


def _labels(model):
    return {f.name: str(f.verbose_name) for f in model._meta.concrete_fields}


def _resolve(model, field_name, value):
    """Valoarea unui câmp legat (id) → denumirea obiectului, ca istoricul să se citească ușor."""
    try:
        field = model._meta.get_field(field_name)
    except Exception:  # noqa: BLE001
        return value
    if value in (None, "") or not getattr(field, "is_relation", False) or not field.related_model:
        if getattr(field, "choices", None) and value is not None:
            return dict(field.choices).get(value, value)
        return value
    obj = field.related_model._default_manager.filter(pk=value).first()
    return str(obj) if obj is not None else value


def _entry(log, model_cache, user):
    model = model_cache.get(log.model)
    if model is None:
        try:
            model = model_cache[log.model] = apps.get_model(log.model)
        except (LookupError, ValueError):
            model = model_cache[log.model] = None
    labels = _labels(model) if model else {}
    changes = []
    for name, value in (log.changes or {}).items():
        if name.startswith("_"):
            continue
        if isinstance(value, list) and len(value) == 2:
            old, new = value
            changes.append({"field": name, "label": labels.get(name, name),
                            "old": _resolve(model, name, old) if model else old,
                            "new": _resolve(model, name, new) if model else new})
        else:
            changes.append({"field": name, "label": labels.get(name, name), "old": None, "new": value})
    return {
        "id": log.pk, "timestamp": log.timestamp, "user": log.username or "sistemul", "action": log.action,
        "model": log.model, "object_id": log.object_id, "object_repr": log.object_repr,
        "is_line": bool(log.parent_model), "line_model": str(model._meta.verbose_name) if model and log.parent_model else "",
        "restored_from": (log.changes or {}).get("_restored_from"), "changes": changes,
        "can_restore": bool(user.is_crm_admin and log.snapshot and not log.parent_model and log.action in ("create", "update")),
    }


def for_object(user, label, object_id):
    model = _model(label)
    _check_view(user, model)
    model_label = model._meta.label
    logs = (AuditLog.objects.filter(Q(model=model_label, object_id=str(object_id))
                                    | Q(parent_model=model_label, parent_id=str(object_id)))
            .order_by("-timestamp", "-id")[:500])
    cache = {}
    return {"model": model_label, "verbose_name": str(model._meta.verbose_name),
            "entries": [_entry(log, cache, user) for log in logs]}


@transaction.atomic
def restore(user, log_id):
    if not user.is_crm_admin:
        raise HistoryError("Revenirea la o versiune anterioară o face doar administratorul.")
    log = AuditLog.objects.filter(pk=log_id).first()
    if log is None or not log.snapshot or log.parent_model:
        raise HistoryError("Versiunea aleasă nu se poate restaura.")
    model = _model(log.model)
    obj = model._default_manager.select_for_update().filter(pk=log.object_id).first()
    if obj is None:
        raise HistoryError("Obiectul nu mai există (a fost șters).")
    status = getattr(obj, "status", None)
    if status is not None and hasattr(obj, "posted_at") and status != "draft":
        raise HistoryError("Documentul este înregistrat: anulați întâi înregistrarea, apoi reveniți la versiune.")
    if hasattr(obj, "date"):
        from .periods import PeriodClosed, check_open

        doc_type = getattr(obj, "DOC_TYPE", "") or model._meta.model_name
        try:
            check_open(getattr(obj, "date", None), user, doc_type)
        except PeriodClosed as exc:
            raise HistoryError(str(exc)) from exc
    excluded = _REGISTRY[model] | {"status", "number", "posted_at", "posted_by"}
    changed = []
    for field in model._meta.concrete_fields:
        if field.name in excluded or field.name not in log.snapshot or field.primary_key or not field.editable:
            continue
        value = log.snapshot[field.name]
        try:
            value = field.to_python(value)
        except Exception:  # noqa: BLE001 – o valoare care nu se mai potrivește se sare
            continue
        if getattr(obj, field.attname) != value:
            setattr(obj, field.attname, value)
            changed.append(field.name)
    if not changed:
        raise HistoryError("Obiectul este deja la această versiune.")
    obj._audit_restored_from = log.pk
    obj.save()
    return {"restored": changed, "object_id": obj.pk}
