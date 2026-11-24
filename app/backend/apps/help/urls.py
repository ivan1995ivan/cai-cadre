from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r"^files/(?P<name>[a-z0-9][a-z0-9-]{0,80}\.(?:docx|webm|mp4))$", views.HelpFileView.as_view()),
    re_path(r"^(?P<lang>ro|ru)/$", views.HelpIndexView.as_view()),
    re_path(r"^(?P<lang>ro|ru)/(?P<key>[a-z0-9/-]+)/$", views.HelpArticleView.as_view()),
]
