"""
WSGI config for pulp_puppet_django project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulp_puppet.forge.settings")

from django.core.wsgi import get_wsgi_application
from pulp.server.webservices.application import SaveEnvironWSGIHandler
from pulp.server import initialization, logs


def wsgi_application():
    """
    Application factory to create, configure, and return a WSGI application
    using the django framework

    :return: wsgi application callable
    """
    try:
        logger = logging.getLogger(__name__)
        logs.start_logging()
        initialization.initialize()
    except initialization.InitializationException, e:
        logger.fatal('*************************************************************')
        logger.fatal('The Pulp Puppet Forge server failed to start due to the following reasons:')
        logger.exception('  ' + e.message)
        logger.fatal('*************************************************************')
        raise e
    except Exception as e:
        logger.fatal('*************************************************************')
        logger.exception('The Pulp Puppet Forge encountered an unexpected failure during initialization')
        logger.fatal('*************************************************************')
        raise e

    logger.info('*************************************************************')
    logger.info('The Pulp Puppet Forge has been successfully initialized')
    logger.info('*************************************************************')

    return SaveEnvironWSGIHandler(get_wsgi_application())
