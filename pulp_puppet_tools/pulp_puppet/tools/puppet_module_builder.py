import os
import sys

from gettext import gettext as _
from optparse import OptionParser, OptionGroup
from subprocess import Popen, PIPE
from hashlib import sha256
from urlparse import urlparse


PKG_DIR = 'pkg'
ARCHIVE_SUFFIX = '.tar.gz'


PATH = _('the path to be searched for puppet modules. the path must be'
         ' relative to the working directory. when not specified,'
         ' the working directory is searched.')

URL = _('the URL to a git repository to be cloned. repositories'
        ' will be cloned into the working directory. cloning will'
        ' set the (-p|--path) to the repository root when (-p|--path) is'
        ' not specified.')

BRANCH = _('the name of a git branch to be checked out.')

TAG = _('the name of a git tag to be checked out.')

FORCE = _('overwrite modules in the output directory.')

WORKING_DIR = _('set the working directory. default: current directory.')

OUTPUT_DIR = _('set the output directory. this can be either an absolute path'
               ' or a path that is relative to the working directory.'
               ' default: working directory.')

CLEAN = _('delete cloned repositories before and after building.')

USAGE = _('%prog <options> [working-dir]')

DESCRIPTION = _(
    'Build puppet modules.'
    ' Search the working directory and build all puppet modules found. The working'
    ' directory is the current directory unless the (-w|--working-dir) option is specified.'
    ' The (-p|--path) option may be used to specify a directory to search/build and'
    ' can be either an absolute path or a path relative to the working directory.'
    ' The archive built using \'puppet module build\' is copied to the output directory'
    ' The output directory is the current directory unless (-o|--output-dir) is'
    ' specified.  The output directory may be either an absolute path or a path that is'
    ' relative to the working directory.'
    ' \nSeveral options are provided for working with git.  Repositories may be cloned'
    ' by specifying the (-u|--url) option. After cloning git repositories, the (-p|--path)'
    ' is set to the root of the cloned repository unless specified explicitly.'
    ' The repository branch may be selected by using the (-b|--branch) option.'
    ' In all cases, when the working directory is a git repository, a \'git pull\' is'
    ' performed to ensure that the repository is up to date.'
    '\n')

BAD_PATH = _('(-p|--path) must be a relative path')
BAD_BRANCH_AND_TAG = _('(-b|--branch) and (-t|--tag) conflict')


def chdir(path):
    """
    Change the working directory.  The main purpose for this method
    is to ignore path=None and display the change of directory to the user.

    :param path: A directory path.
    :type path: str
    """
    if path:
        print 'cd %s' % path
        os.chdir(path)


def shell(command, exit_on_err=True):
    """
    Invoke shell commands and return the exit-code and any
    output written by the command to stdout.

    :param command: The command to invoke.
    :type command: str
    :param exit_on_err: Exit the script if the command fails.
    :type exit_on_err: bool
    :return: (exit-code, output)
    :rtype: tuple
    """
    print command
    call = command.split()
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    p = Popen(call, stdout=PIPE, stderr=PIPE, env=env)
    status, output = p.wait(), p.stdout.read()
    if exit_on_err and status != os.EX_OK:
        print p.stderr.read()
        sys.exit(status)
    return status, output


def get_options():
    """
    Parse and return command line options.
    Sets defaults and validates options.

    :return: The options passed by the user.
    :rtype: optparse.Values
    """
    parser = OptionParser(usage=USAGE, description=DESCRIPTION)
    parser.add_option('-w', '--working-dir', dest='working_dir', help=WORKING_DIR)
    parser.add_option('-o', '--output-dir', dest='output_dir', help=OUTPUT_DIR)
    parser.add_option('-c', '--clean', default=False, action='store_true', help=CLEAN)
    parser.add_option('-f', '--force', default=False, action='store_true', help=FORCE)
    git = OptionGroup(parser, 'git')
    git.add_option('-u', '--url', help=URL)
    git.add_option('-b', '--branch', help=BRANCH)
    git.add_option('-t', '--tag', help=TAG)
    parser.add_option('-p', '--path', help=PATH)
    parser.add_option_group(git)
    (opts, args) = parser.parse_args()

    # validate
    if opts.path and opts.path.startswith('/'):
        print BAD_PATH
        sys.exit(os.EX_USAGE)
    if opts.branch and opts.tag:
        print BAD_BRANCH_AND_TAG
        sys.exit(os.EX_USAGE)

    # clean url
    if opts.url:
        opts.url = opts.url.rstrip('/')

    # expand paths
    if opts.working_dir:
        opts.working_dir = os.path.expanduser(opts.working_dir)
    if opts.output_dir:
        opts.output_dir = os.path.expanduser(opts.output_dir)

    # set defaults
    if not opts.working_dir:
        if args:
            opts.working_dir = args[0]
        else:
            opts.working_dir = os.getcwd()
    if not opts.output_dir:
        opts.output_dir = opts.working_dir
    return opts


def set_origin(options):
    """
    Detect whether the working-directory is a git repository
    and set the origin URL in the *options* passed in.

    :param options: The command line options.
    :type options: optparse.Options
    """
    status, output = shell('git status', False)
    if status != 0:
        # not in a git repository
        options.origin = None
        return
    status, output = shell('git remote show -n origin')
    for line in output.split('\n'):
        line = line.strip()
        if line.startswith('Fetch URL:'):
            url = line.split(':', 1)[1]
            options.origin = url.strip()


def git_clone(options):
    """
    Clone the git repository only if the user specified to do so using
    the (-u|--url) option.  Assuming the user is cloning the repository
    for the purpose of building puppet modules within it, the *path* option
    is set to root of the cloned repository for convenience.

    :param options: The command line options.
    :type options: optparse.Options
    """
    if not options.url:
        # cloning not requested
        return
    shell('git clone --recursive %s' % options.url)
    if not options.path:
        url = urlparse(options.url)
        path = os.path.basename(url.path)
        path = os.path.splitext(path)[0]
        options.path = path


def git_checkout(options):
    """
    Perform a git checkout of a user specified branch or tag only if
    the working-directory is a git repository.  A git-fetch is done prior
    to the checkout to ensure that branches and tags exist in the local repository.
    Finally, unless a tag has been checked out, a git-pull is performed to ensure
    the local repository is up to date with origin.

    :param options: The command line options.
    :type options: optparse.Options
    """
    if not options.origin:
        # not in a git repository
        return
    shell('git fetch')
    shell('git fetch --tags')
    if options.branch:
        shell('git checkout %s' % options.branch)
        shell('git pull')
        return
    if options.tag:
        shell('git checkout %s' % options.tag)
        return


def find_modules():
    """
    Search for puppet (source) modules to build and return a list of paths.
    Puppet modules are identified by finding `Modulefile` or `metadata.json`
    files.  Once found, the *module* directory path is included in the result.

    :return: A set of puppet module directory paths.
    :rtype: set
    """
    modules = set()
    modules_status, modules_output = shell('find . -name Modulefile -o -name metadata.json')
    paths = modules_output.strip().split('\n')
    for path in paths:
        path = path.strip()
        path_pieces = path.split('/')
        # Puppet makes a PKG_DIR with a copy of the module when built, so don't include those.
        if len(path_pieces) >= 3 and path_pieces[-3] == PKG_DIR:
            continue
        modules.add(os.path.dirname(path))
    return modules


def publish_module(module_dir, output_dir, force=False):
    """
    Publish built puppet modules.
    This mainly consists of copying the tarball from the pkg/
    directory to the user specified output directory.  The
    output directory is created as needed.

    :param module_dir: The module source directory path.
    :type module_dir: str
    :param output_dir: The user specified output directory path.
    :type output_dir: str
    :param force: Overwrite any existing files in output dir if True
    :type force: bool
    """
    shell('mkdir -p %s' % output_dir)
    for name in os.listdir(module_dir):
        if not name.endswith(ARCHIVE_SUFFIX):
            continue

        output_path = os.path.join(output_dir, name)
        if os.path.isfile(output_path) and not force:
            print "Skipping %s as the file exists" % name
            continue

        path = os.path.join(module_dir, name)
        shell('cp %s %s' % (path, output_dir))


def build_puppet_modules(options):
    """
    Build puppet modules found during the search and publish
    (copy) them to the user specified output directory.

    :param options: The command line options.
    :type options: optparse.Options
    """
    for path in find_modules():
        shell('puppet module build %s' % path)
        pkg_dir = os.path.join(path, PKG_DIR)
        publish_module(pkg_dir, options.output_dir, options.force)


def digest(path):
    """
    Calculate the SHA256 hex digest for the file at the
    specified path.

    :param path: An absolute path to a file.
    :type path: str
    :return: The hex digest.
    :rtype: str
    """
    h = sha256()
    with open(path) as fp:
        h.update(fp.read())
    return h.hexdigest()


def build_manifest(options):
    """
    Build the pulp manifest.
    The pulp manifest is a file listing the built puppet tarballs.
    Each file is listed as an entry on a separate line and has the
    format of: <name>,<sha256>,<size>.

    :param options: The command line options.
    :type options: optparse.Options
    """
    _dir = os.getcwd()
    chdir(options.output_dir)
    with open('PULP_MANIFEST', 'w+') as fp:
        for path in os.listdir('.'):
            if not path.endswith(ARCHIVE_SUFFIX):
                continue
            fp.write(path)
            fp.write(',%s' % digest(path))
            fp.write(',%s\n' % os.path.getsize(path))
    chdir(_dir)


def clean(options):
    """
    Clean up before and after building when specified by the
    user (-c|clean) command line option.

    :param options: The command line options.
    :type options: optparse.Options
    """
    if options.url and options.clean:
        url = urlparse(options.url)
        path = os.path.basename(url.path)
        path = os.path.splitext(path)[0]
        path = os.path.join(options.working_dir, path)
        shell('rm -rf %s' % path)


def main():
    """
    The command entry point.
    """
    _dir = os.getcwd()
    options = get_options()
    clean(options)
    chdir(options.working_dir)
    git_clone(options)
    chdir(options.path)
    set_origin(options)
    git_checkout(options)
    build_puppet_modules(options)
    build_manifest(options)
    chdir(_dir)
    clean(options)
