# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

# Find and eradicate all .pyc files, so they don't ruin everything
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
find $PROJECT_DIR -name "*.pyc" -delete

PACKAGES="pulp_puppet"

# Test Directories
TESTS="pulp_puppet_common/test/unit pulp_puppet_extensions_admin/test/unit pulp_puppet_plugins/test/unit"

nosetests --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
