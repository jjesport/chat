from django.urls import path
from . import views

urlpatterns = [
    path('messages', views.get_messages),
    path('stats', views.get_stats),
]
