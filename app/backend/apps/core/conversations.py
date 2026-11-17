"""Conversațiile pe obiecte și mesajele între utilizatori.

Orice obiect cu istoric (comandă, client, factură, aviz, ofertă, document de stoc...) poate avea o conversație. La un
mesaj nou primesc notificare: cei care au mai scris în ea, responsabilul obiectului (managerul / cine l-a creat) și cei
menționați (aleși din listă sau scriși ca @utilizator). Notificarea duce la obiect.
"""
import re

from django.contrib.auth import get_user_model
from django.db import transaction

from .history import HistoryError, _check_view, _model
from .models import Comment, Notification

MENTION = re.compile(r"@([\w.\-]+)")


def _object(user, label, object_id):
    model = _model(label)
    _check_view(user, model)
    obj = model._default_manager.filter(pk=object_id).first()
    if obj is None:
        raise HistoryError("Obiectul nu există.")
    return model, obj


def _owners(obj):
    """Responsabilii obiectului: managerul și cine l-a creat (dacă modelul îi are)."""
    owners = set()
    for attr in ("manager_id", "created_by_id", "user_id"):
        value = getattr(obj, attr, None)
        if value:
            owners.add(value)
    return owners


def listing(user, label, object_id):
    model, _obj = _object(user, label, object_id)
    rows = Comment.objects.filter(model=model._meta.label, object_id=str(object_id)).select_related("author") \
        .prefetch_related("mentions")
    return [{"id": c.pk, "author": str(c.author) if c.author else "—", "author_id": c.author_id, "text": c.text,
             "created_at": c.created_at, "mentions": [str(u) for u in c.mentions.all()],
             "can_delete": c.author_id == user.pk or user.is_crm_admin} for c in rows]


def count(user, label, object_id):
    model = _model(label)
    return Comment.objects.filter(model=model._meta.label, object_id=str(object_id)).count()


@transaction.atomic
def post(user, label, object_id, text, mention_ids=None, link=""):
    text = (text or "").strip()
    if not text:
        raise HistoryError("Scrieți mesajul.")
    model, obj = _object(user, label, object_id)
    users = get_user_model().objects.filter(is_active=True)
    mentioned = set(users.filter(pk__in=mention_ids or []).values_list("pk", flat=True))
    names = MENTION.findall(text)
    if names:
        mentioned |= set(users.filter(username__in=names).values_list("pk", flat=True))
    comment = Comment.objects.create(model=model._meta.label, object_id=str(obj.pk), object_repr=str(obj)[:200],
                                     link=link[:300], author=user, text=text)
    comment.mentions.set(mentioned)
    previous = set(Comment.objects.filter(model=comment.model, object_id=comment.object_id)
                   .exclude(author__isnull=True).values_list("author_id", flat=True))
    recipients = (previous | _owners(obj) | mentioned) - {user.pk}
    title_obj = f"{model._meta.verbose_name} {obj}"
    for recipient in users.filter(pk__in=recipients):
        title = (f"{user} v-a menționat: {title_obj}" if recipient.pk in mentioned else f"{user} a scris despre {title_obj}")
        Notification.send(recipient, title[:200], text[:500], level="task" if recipient.pk in mentioned else "info",
                          kind="comment", link=link, created_by=user)
    return comment


def delete(user, comment_id):
    comment = Comment.objects.filter(pk=comment_id).first()
    if comment is None:
        raise HistoryError("Mesajul nu există.")
    if comment.author_id != user.pk and not user.is_crm_admin:
        raise HistoryError("Se șterge doar mesajul propriu.")
    comment.delete()


def send_message(user, user_ids, title, message="", link=""):
    """Mesaj / notificare de la un utilizator către colegi (clopoțelul lor)."""
    title = (title or "").strip()
    if not title:
        raise HistoryError("Scrieți mesajul.")
    recipients = get_user_model().objects.filter(is_active=True, pk__in=user_ids or []).exclude(pk=user.pk)
    if not recipients:
        raise HistoryError("Alegeți cui trimiteți.")
    for recipient in recipients:
        Notification.send(recipient, f"{user}: {title}"[:200], message, level="task", kind="message", link=link[:300],
                          created_by=user)
    return len(recipients)
