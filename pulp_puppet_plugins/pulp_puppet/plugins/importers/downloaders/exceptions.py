class InvalidFeed(Exception):
    def __init__(self, feed, *args):
        Exception.__init__(self, feed, *args)
        self.feed = feed


class UnsupportedFeedType(Exception):
    def __init__(self, feed_type, *args):
        Exception.__init__(self, feed_type, *args)
        self.feed_type = feed_type


class FileRetrievalException(Exception):
    """
    Base class for all exceptions related to trying to retrieve files, either
    metadata documents or modules. This should only directly be used if there
    is no more specific subclass.
    """
    def __init__(self, location, *args):
        """
        :param location: where the document was attempted to be read from
        :type  location: str
        """
        Exception.__init__(self, location, *args)
        self.location = location

    def __str__(self):
        template = '%s: %s'
        return template % (self.__class__.__name__, self.location)


class FileNotFoundException(FileRetrievalException):
    """
    Raised if a requested file cannot be found.
    """
    pass


class UnauthorizedException(FileRetrievalException):
    """
    Raised if a file fails to be retrieved because it could not be read
    (e.g. 401 from a web request, no read perms for a local read).
    """
    pass
