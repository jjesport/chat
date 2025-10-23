"""
URL configuration for chat_api project.

Este archivo define las rutas principales (URLs) del proyecto Django.
Su función es dirigir las solicitudes HTTP hacia las vistas correspondientes,
ya sea del panel administrativo o de las aplicaciones internas (por ejemplo, messages_app).

Documentación oficial:
https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

# Lista principal de rutas del proyecto
urlpatterns = [
    # -------------------------------------------------------------------------
    # 1️ Ruta del panel administrativo de Django
    # -------------------------------------------------------------------------
    # URL: http://localhost:8000/admin/
    # Permite acceder al panel de administración integrado en Django,
    # donde se pueden gestionar modelos, usuarios, permisos, etc.
    path('admin/', admin.site.urls),

    # -------------------------------------------------------------------------
    # 2️ Rutas de la API principal del proyecto
    # -------------------------------------------------------------------------
    # URL base: http://localhost:8000/api/
    # Esta ruta redirige todas las solicitudes que comienzan con /api/
    # hacia el archivo de rutas definido dentro de la aplicación messages_app.
    #
    # Por ejemplo:
    #   - Si en messages_app/urls.py existe:
    #         path('messages/', views.get_messages)
    #   - Entonces la ruta completa será:
    #         http://localhost:8000/api/messages/
    #
    # Esto mejora la organización y modularidad del proyecto.
    path('api/', include('messages_app.urls')),
]
