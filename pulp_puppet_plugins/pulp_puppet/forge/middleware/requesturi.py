class UpdatePathInfo(object):
    """
    Rewrite request.path_info so that it contains the full URL requested. The full URL is composed
    of the WSGIScriptAlias that is passed in the SCRIPT_NAME header. '/releases.json' becomes
    '/api/v1/releases.json', '/<consumer_id>/<repo_id>/api/v1/releases.json' becomes
    '/pulp_puppet/forge/<consumer_id>/<repo_id>/api/v1/releases.json' and '/releases' becomes
    '/v3/releases'.
    """

    def process_request(self, request):
        """
        Don't just blindly prepend the request.META['SCRIPT_NAME'] because the application could be
        hosted at a path that Django application is not aware of.
        :param request:
        :return:
        """

        request.path_info = request.META['SCRIPT_NAME'] + request.path_info
