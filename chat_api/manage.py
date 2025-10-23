#!/usr/bin/env python
"""
Archivo: manage.py

Descripción:
----------------------
Este archivo es el punto de entrada principal para interactuar con el proyecto Django
desde la línea de comandos. Proporciona acceso a las utilidades administrativas
y de gestión del framework, tales como ejecutar el servidor, crear migraciones,
aplicar cambios en la base de datos, crear usuarios administradores, entre otras.

Ejemplos de uso común:
----------------------
- Ejecutar el servidor de desarrollo:
      python manage.py runserver

- Crear migraciones de base de datos:
      python manage.py makemigrations

- Aplicar migraciones:
      python manage.py migrate

- Crear un superusuario (acceso a /admin/):
      python manage.py createsuperuser

- Probar la configuración o ejecutar scripts personalizados:
      python manage.py shell
"""
import os
import sys


def main():
    """
    Función principal encargada de iniciar las tareas administrativas de Django.
    Configura el entorno del proyecto, asegurándose de que Django pueda acceder
    correctamente a los módulos definidos en `chat_api.settings`.
    """
    # Define la variable de entorno para las configuraciones de Django.
    # Esto indica a Django dónde encontrar el archivo settings.py del proyecto.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_api.settings')
    try:
        # Importa la función que permite ejecutar comandos desde la terminal.
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Manejo de errores en caso de que Django no esté instalado o configurado.
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # Ejecuta el comando recibido desde la línea de comandos.
    # Ejemplo: python manage.py runserver
    execute_from_command_line(sys.argv)

# Punto de inicio del script
if __name__ == '__main__':
    main()
