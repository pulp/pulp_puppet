import unittest

from django.core.urlresolvers import resolve, reverse, NoReverseMatch


def assert_url_match(expected_url, url_name, *args, **kwargs):
        """
        Generate a url given args and kwargs and pass it through Django's reverse and
        resolve functions.

        Example use to match a url /v2/tasks/<task_argument>/:
        assert_url_match('/v2/tasks/example_arg/', 'tasks', task_argument='example_arg')

        :param expected_url: the url that should be generated given a url_name and args
        :type  expected_url: str
        :param url_name    : name given to a url as defined in the urls.py
        :type  url_name    : str
        :param args        : optional positional arguments to place into a url's parameters
                             as specified by urls.py
        :type  args        : tuple
        :param kwargs      : optional named arguments to place into a url's parameters as
                             specified by urls.py
        :type  kwargs      : dict
        """
        try:
            # Invalid arguments will cause a NoReverseMatch.
            url = reverse(url_name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            raise AssertionError(
                "Name: '{0}' could match a url with args '{1}'"
                "and kwargs '{2}'".format(url_name, args, kwargs)
            )

        else:
            # If the url exists but is not the expected url.
            if url != expected_url:
                raise AssertionError(
                    'url {0} not equal to expected url {1}'.format(url, expected_url))

            # Run this url back through resolve and ensure that it matches the url_name.
            matched_view = resolve(url)
            if matched_view.url_name != url_name:
                raise AssertionError('Url name {0} not equal to expected url name {1}'.format(
                    matched_view.url_name, url_name)
                )


class TestForgetUrls(unittest.TestCase):
    """
    Test the matching of the releases urls for all versions
    """

    def test_match_post_36_releases(self):
        """
        Test url matching for post_36_releases.
        """
        url = '/v3/releases'
        url_name = 'post_36_releases'
        assert_url_match(url, url_name)

    def test_match_post_33_releases(self):
        """
        Test url matching for post_33_releases.
        """
        url = '/pulp_puppet/forge/repository/repo-id/api/v1/releases.json'
        url_name = 'post_33_releases'
        assert_url_match(url, url_name, 'repository', 'repo-id')

    def test_match_pre_33_releases(self):
        """
        Test url matching for post_33_releases.
        """
        url = '/api/v1/releases.json'
        url_name = 'pre_33_releases'
        assert_url_match(url, url_name)
