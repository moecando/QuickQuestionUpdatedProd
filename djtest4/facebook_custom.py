
from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_facebook import exceptions as facebook_exceptions, \
    settings as facebook_settings
from django_facebook.connect import CONNECT_ACTIONS, connect_user
from django_facebook.decorators import facebook_required_lazy, facebook_required
from django_facebook.utils import next_redirect, get_registration_backend, \
    to_bool, error_next_redirect, get_instance_for
from open_facebook import exceptions as open_facebook_exceptions
from open_facebook.utils import send_warning
from django_facebook.views import _connect
import logging


#THIS IS AN EXPERIMENT TO SEE IF I CAN COPY CODE FROM DJANGO_FACEBOOK's views.py AND use it to override login
#NOT USED IN PRODUCTION

@csrf_exempt
@facebook_required(scope=[
    'email', 'user_about_me', 'user_birthday', 'user_website', 'publish_stream'])
def custom_connect(request, graph):
    '''
    Exception and validation functionality around the _connect view
    Separated this out from _connect to preserve readability
    Don't bother reading this code, skip to _connect for the bit you're interested in :)
    '''
    backend = get_registration_backend()
    context = RequestContext(request)

    # validation to ensure the context processor is enabled
    if not context.get('FACEBOOK_APP_ID'):
        message = 'Please specify a Facebook app id and ensure the context processor is enabled'
        raise ValueError(message)

    try:
        response = _connect(request, graph)
    except open_facebook_exceptions.FacebookUnreachable, e:
        # often triggered when Facebook is slow
        warning_format = u'%s, often caused by Facebook slowdown, error %s'
        warn_message = warning_format % (type(e), e.message)
        send_warning(warn_message, e=e)
        additional_params = dict(fb_error_or_cancel=1)
        response = backend.post_error(request, additional_params)

    return response
