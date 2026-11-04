# NOTE (Unit Testing Platform): this file was MODIFIED from the upstream Lizard 1.24.3 source.
# The upstream file imports 27 language readers; this application analyses only C, C++ and
# Python, so only those readers are shipped. The two functions below are otherwise identical
# to upstream (same order of the remaining readers, same matching logic).
# See third_party/lizard/MODIFICATIONS.md.
''' programming languages of lizard '''

from .clike import CLikeReader
from .python import PythonReader


def languages():
    return [
        CLikeReader,
        PythonReader,
    ]


def get_reader_for(filename):
    for lan in languages():
        if lan.match_filename(filename):
            return lan
