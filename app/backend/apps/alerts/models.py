"""Notificările despre termene (Etapa 5): ce s-a trimis deja cui, ca aceeași alertă să nu se repete în fiecare noapte."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class AlertLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alert_logs")
    key = models.CharField("Cheia alertei", max_length=120)
    sent_at = models.DateTimeField(default=timezone.now)
    emailed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="uniq_alert_log")]
        verbose_name = "Alertă trimisă"
