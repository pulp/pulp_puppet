"""
WSGI config for pulp_django project.
It exposes the WSGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""
from pulp_puppet.forge.wsgi import wsgi_application


application = wsgi_application()
