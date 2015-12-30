import base64
import re
import urllib

from django.http import HttpResponseNotFound, HttpResponse, HttpResponseBadRequest
from django.views.generic import View
from pulp.server.webservices.views.util import generate_json_response

from pulp_puppet.forge import releases


MODULE_PATTERN = re.compile('(^[a-zA-Z0-9]+)(/|-)([a-zA-Z0-9_]+)$')
MODULE_PATH_PARAM_PATTERN = re.compile('(^[a-zA-Z0-9]+)(/|-)([a-zA-Z0-9_]+)(/|-)([a-zA-Z0-9_.-]+)$')
POST_36_URL_PATTERN = re.compile('^/v3/releases/(.+)')


class ReleasesView(View):

    REPO_RESOURCE = 'repository'
    CONSUMER_RESOURCE = 'consumer'

    def get(self, request, resource_type=None, resource=None):
        """
        Credentials here are not actually used for authorization, but instead
        are used to identify:

            consumer ID in the username field
            repository ID in the password field

        This is to work around the fact that the "puppet module install"
        command has hard-coded absolute paths, so we cannot put consumer or
        repository IDs in the URL's path.
        """
        hostname = request.get_host()
        if resource_type is not None:
            if resource_type == self.REPO_RESOURCE:
                credentials = ('.', resource)
            elif resource_type == self.CONSUMER_RESOURCE:
                credentials = (resource, '.')
            else:
                return HttpResponseNotFound()

        else:
            credentials = self._get_credentials(request.META)
            if not credentials:
                return HttpResponse('Unauthorized', status=401)

        get_dict = self._get_parameters(request.GET, request.path_info)
        if isinstance(get_dict, HttpResponse):
            return get_dict
        module_name = get_dict.get('module')
        version = get_dict.get('version')

        data = self.get_releases(*credentials, module_name=module_name, version=version,
                                 hostname=hostname)
        if isinstance(data, HttpResponse):
            return data
        return self.format_results(data, get_dict, request.path_info)

    def get_releases(self, *args, **kwargs):
        """
        Get the list of matching releases

        :return: The matching modules
        :rtype: dict
        """
        return releases.view(*args, **kwargs)

    def format_results(self, data, get_dict, path):
        """
        Format the results and begin streaming out to the caller

        :param data: The module data to stream back to the caller
        :type data: dict
        :param get_dict: The GET parameters
        :type get_dict: dict
        :return: the body of what should be streamed out to the caller
        :rtype: str
        """
        return generate_json_response(data)

    @staticmethod
    def _get_credentials(headers):
        """
        :return: username and password provided as basic auth credentials
        :rtype:  str, str
        """
        auth = headers.get('HTTP_AUTHORIZATION')
        if auth:
            encoded_credentials = re.sub('^Basic ', '', auth)
            try:
                username, password = base64.decodestring(encoded_credentials).split(':')
            # raised by the split if the decoded string lacks a ':'
            except ValueError:
                return
            return username, password

    @staticmethod
    def _get_parameters(get_dict, path):
        """
        Get the parameters of the HTTP request

        :param get_dict: The GET parameters
        :type get_dict: dict
        :param path: The path of the HTTP request
        :type path: str
        :return: dictionary with all of the request parameters,
                 or HttpResponseBadRequest if invalid
        :rtype: dict
        """
        module_parameters = get_dict.copy()
        module_name = module_parameters.get('module', '')
        match = MODULE_PATTERN.match(module_name)
        if match:
            normalized_name = u'%s/%s' % (match.group(1), match.group(3))
            module_parameters['module'] = normalized_name
            return module_parameters
        else:
            return HttpResponseBadRequest('Module name is missing.')


class ReleasesPost36View(ReleasesView):

    @staticmethod
    def _get_parameters(get_dict, path):
        """
        Get the parameters of the HTTP request

        :param get_dict: The GET parameters
        :type get_dict: dict
        :param path: The path of the HTTP request
        :type path: str
        :return: dictionary with all of the request parameters,
                 or HttpResponseBadRequest if invalid
        :rtype: dict
        """
        url_match = POST_36_URL_PATTERN.match(path)
        if url_match:
            path_parameter = url_match.group(1)
            parameter_match = MODULE_PATH_PARAM_PATTERN.match(path_parameter)
            module_parameters = {}
            if parameter_match:
                normalized_name = u'%s/%s' % (parameter_match.group(1), parameter_match.group(3))
                module_parameters['module'] = normalized_name
                module_parameters['version'] = parameter_match.group(5)
                module_parameters['path'] = path_parameter
                return module_parameters
            else:
                return HttpResponseBadRequest('Module parameter is missing.')
        else:
            return ReleasesView._get_parameters(get_dict, path)

    @staticmethod
    def _format_query_string(base_url, module_name, module_version, offset, limit):
        """
        Build the query string to be used for creating

        :param base_url: The context root to sue when generating a releases query.
        :type base_url: str
        :param module_name: The module name to add to the query string
        :type module_name: str
        :param module_version: The version of the module to encode in the query string
        :type module_version: str
        :param offset: The offset to encode for pagination
        :type offset: int
        :param limit: The max number of items to show on a page
        :type limit: int
        :return: The encoded URL for the specified query arguments
        :rtype: str
        """
        query_args = {'module': module_name,
                      'offset': offset,
                      'limit': limit}
        if module_version:
            query_args['version'] = module_version

        return '%s?%s' % (base_url, urllib.urlencode(query_args))

    @staticmethod
    def _format_module(module_name, module):
        """
        Format the contents of the module dictionary and return the result

        :param module_name: The name of the module
        :type module_name: str
        :param module: A dictionary with all of the module's information
        :type module: dict
        :return: A dictionary containing module information of interest to the caller
        :rtype: dict
        """
        formatted_dependencies = []
        for dep in module.get('dependencies', []):
            formatted_dependencies.append({
                'name': dep[0],
                'version_requirement': dep[1]
            })
        module_data = {
            'metadata': {
                'name': module_name,
                'version': module.get('version'),
                'dependencies': formatted_dependencies
            },
            'file_uri': module.get('file'),
            'file_md5': module.get('file_md5')
        }
        return module_data

    def get_releases(self, *args, **kwargs):
        """
        Get the list of matching releases

        :return: The matching modules
        :rtype: dict
        """
        return releases.view(*args, recurse_deps=False, view_all_matching=True, **kwargs)

    def format_results(self, data, get_dict, path):
        """
        Format the results and begin streaming out to the caller for the v3 API

        :param data: The module data to stream back to the caller
        :type data: dict
        :param get_dict: The GET parameters
        :type get_dict: dict
        :param path: The path starting with parameters
        :type get_dict: dict
        :return: the body of what should be streamed out to the caller
        :rtype: str
        """
        module_name = get_dict.get('module', '')
        path_parameter = get_dict.get('path', None)
        module_list = data.get(module_name)

        if not path_parameter:
            limit = int(get_dict.get('limit', 20))
            current_offset = int(get_dict.get('offset', 0))
            module_version = get_dict.get('version', None)

            first_path = self._format_query_string(path, module_name, module_version,
                                                   0, limit)
            current_path = self._format_query_string(path, module_name, module_version,
                                                     current_offset, limit)
            if current_offset > 0:
                previous_path = self._format_query_string(path, module_name, module_version,
                                                          current_offset - limit, limit)
            else:
                previous_path = None

            formatted_results = {
                'pagination': {
                    'limit': limit,
                    'offset': current_offset,
                    'first': first_path,
                    'previous': previous_path,
                    'current': current_path,
                    'next': None,
                    'total': 1
                },
                'results': []
            }
            total_count = len(module_list)

            for module in module_list[current_offset: (current_offset + limit)]:
                formatted_module = self._format_module(module_name, module)
                formatted_results['results'].append(formatted_module)

            formatted_results['pagination']['total'] = total_count

            if total_count > (current_offset + limit):
                next_path = self._format_query_string(path, module_name, module_version,
                                                      current_offset + limit, limit)
                formatted_results['pagination']['next'] = next_path
        else:
            formatted_module = self._format_module(module_name, module_list[0])
            formatted_results = formatted_module

        return generate_json_response(formatted_results)
