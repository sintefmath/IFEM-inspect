import click
import IPython
from IPython.terminal.embed import InteractiveShellEmbed
from os import listdir
from os.path import splitext, isfile
import readline
import sys
import textwrap

import ifem
from ifem.result import Result
from ifem.script import exec_string


class Config:

    def __init__(self):
        self.basename = None

    def result(self):
        if not self.basename:
            raise FileNotFoundError('No result file found')
        return Result(self.basename)

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--file', 'basename', type=str, default=None, required=False,
              help=textwrap.dedent("""
              The IFEM result file to inspect. May be the HDF5 file, the
              sidecar XML file or their common basename. If omitted,
              ifem-inspect looks for candidates in the cwd. Note, some commands
              do not require a file.
              """).replace('\n', ' '))
@pass_config
def main(config, basename):
    """Inspect IFEM result files."""
    if basename:
        basename, _ = splitext(args[0])
        if not isfile(basename + '.hdf5') or not isfile(basename + '.xml'):
            print('No such result file found: {}'.format(basename), file=sys.stderr)
            sys.exit(1)
    else:
        files = set(listdir('.'))
        basenames = {splitext(fn)[0] for fn in files}
        basenames = {bn for bn in basenames if
                     bn + '.hdf5' in files and bn + '.xml' in files and
                     isfile(bn + '.hdf5') and isfile(bn + '.xml')}
        if len(basenames) == 1:
            basename = next(iter(basenames))

    config.basename = basename


@main.command()
@pass_config
def interactive(config):
    """Enter REPL mode."""
    with config.result() as res:
        banner = '\n'.join([
            'Python ' + ' '.join(sys.version.split('\n')),
            'IPython ' + IPython.__version__,
            'IFEM-Inspect ' + ifem.__version__,
            'Result file: ' + res.basename,
        ]) + '\n'

        ipshell = InteractiveShellEmbed(banner1=banner)
        ipshell(local_ns={}, module=res.namespace())


if __name__ == '__main__':
    try:
        main()
    except e:
        print(e)
        sys.exit(1)
