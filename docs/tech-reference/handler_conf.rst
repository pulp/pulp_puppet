Handler Configuration
=====================

These options can be passed to a handler request.

``repo_id``
 Option ID for a repository that should be used to fulfill an install request.

``whole_repo``
 Boolean value for an install request indicating if the entire repository
 should be installed. Defaults to ``False``. If ``True``, a ``repo_id`` must
 also be specified.
