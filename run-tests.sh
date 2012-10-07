# Please keep the following in alphabetical order so it's easier to determine
# if something is in the list

PACKAGES="pulp_puppet"

# Test Directories
TESTS="pulp_puppet_common/test/unit pulp_puppet_extensions_admin/test/unit pulp_puppet_plugins/test/unit"

nosetests --with-coverage --cover-html --cover-erase --cover-package $PACKAGES $TESTS
