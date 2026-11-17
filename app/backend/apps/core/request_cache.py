"""Memorie pe durata unei cereri HTTP pentru citirile repetate ale acelorași rânduri de configurare (Constantele firmei,
setările de sistem): listele și înregistrarea documentelor le cereau o dată pe fiecare rând / linie.

În afara unei cereri (comenzi, fire de lucru în fundal) nu se memorează nimic: fiecare citire merge la bază, ca înainte.
"""
import contextvars

_store = contextvars.ContextVar("crm_request_cache", default=None)
_MISSING = object()


def get(key, loader):
    store = _store.get()
    if store is None:
        return loader()
    value = store.get(key, _MISSING)
    if value is _MISSING:
        value = store[key] = loader()
    return value


def forget(key):
    store = _store.get()
    if store is not None:
        store.pop(key, None)


class RequestCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _store.set({})
        try:
            return self.get_response(request)
        finally:
            _store.reset(token)
