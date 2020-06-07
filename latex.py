#!env/bin/python
"NOTE: make sure you set the python interpreter correctly"

"""
Pandoc filter to process raw latex math environments into images.
Assumes that pdflatex is in the path, and that the standalone
package is available.  Also assumes that ImageMagick's convert
is in the path. Images are put in the `latex_images` directory.

Notes
-----
have to print to stderr, because everything normally printed will get
piped to the next command.

apparently, also have to make this script executable:

```bash
chmod u+x latex.py
```
"""

import sys

sys.stderr.write(sys.version)

import os
import sys
from subprocess import call
from tempfile import TemporaryDirectory
from contextlib import contextmanager
from textwrap import dedent
import hashlib

from pandocfilters import toJSONFilter, Image


def format_latex(code):
    """
    some notes on the latex here:
    https://tex.stackexchange.com/questions/50162/how-to-make-a-standalone-document-with-one-equation
    """

    s = dedent(r"""
    \documentclass{article}
    \usepackage{amsmath}
    \usepackage[active,tightpage]{preview}
    \PreviewEnvironment{equation*}
    \begin{document}
    \begin{equation*}
    <<__code__>>
    \end{equation*}
    \end{document}
    """).strip()

    code = dedent(code).strip()
    s = s.replace('<<__code__>>', code)

    return s



@contextmanager
def temp_cd():
    """ Create a temporary directory and `cd` to it while
    in the context manager.

    Return to the calling directory `cwd`, and delete the
    temporary directory when done.
    """
    with TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            yield cwd
        finally:
            os.chdir(cwd)

def write_file(fname, src):
    with open(fname, 'w') as f:
        f.write(src)


def get_filename(src, opts, dirname='latex_images'):
    """
    Hash the full source and options to get a filename,
    in case either the formatting or options changes.
    """
    s = src + str(opts)
    s = hashlib.sha1(s.encode(sys.getfilesystemencoding())).hexdigest()
    s = dirname + '/' + s + '.png'

    try:
        os.mkdir(dirname)
        sys.stderr.write('Created directory ' + dirname + '\n')
    except OSError:
        pass

    return s

def latex2image(latex_src):
    latex_src = format_latex(latex_src)
    opts = [
        '-density', '600',
        '-quality', '100',
        #'-trim', # images expand to be too big on the page!
    ]
    outfile = get_filename(latex_src, opts)

    if not os.path.isfile(outfile):
        tex = 'temp_img.tex'
        pdf = 'temp_img.pdf'
        with temp_cd() as cwd:
            write_file(tex, latex_src)
            call(["pdflatex", tex], stdout=sys.stderr)
            call(["convert", *opts, pdf, f'{cwd}/{outfile}'])

        sys.stderr.write('Created image ' + outfile + '\n')

    return outfile


def latex_equation(key, value, format, _):
    """
    Notes
    -----

    When using the pipes mode, `format` is the empty string
    When using the `--filter` option, `format == 'docx'`!
    We could use this to have the filter handle pdf/docx output properly.
    """
    if key == 'Math':
        thing, code = value
        if thing['t'] == 'DisplayMath':
            #print(f'The format is: {format}', file=sys.stderr)
            return Image(['', [], []], [], [latex2image(code), ""])

    return None

if __name__ == "__main__":
    toJSONFilter(latex_equation)
