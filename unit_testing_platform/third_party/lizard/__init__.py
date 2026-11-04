"""Locally integrated source-code analysis core (C, C++ and Python).

This package is a trimmed copy of the open-source "Lizard" code analyzer, version
1.24.3, by Terry Yin and other contributors (https://github.com/terryyin/lizard),
distributed under the MIT License (see LICENSE.txt in this directory; the upstream
facade file ``lizard.py`` additionally carries an Apache-2.0 header, so that license
text is shipped too: LICENSE-Apache-2.0.txt). It is NOT independently written code.

What is here, what was changed and why: see README.md and MODIFICATIONS.md in this
directory and THIRD_PARTY_NOTICES.md at the repository root.

This file is new (written for this application). ``analyze_file`` below assembles the
same default pipeline that upstream builds in ``lizard_core/extensions.py``
(``get_extensions([])``) and ``lizard_core/analysis.py`` (``analyze_file = FileAnalyzer(...)``).
Nothing here imports the separately installable ``lizard`` package, and nothing here
touches the network.
"""
from .lizard_core.file_analyzer import (
    FileAnalyzer, preprocessing, comment_counter, line_counter, token_counter,
    condition_counter,
)

#: Upstream release this code was taken from.
UPSTREAM_VERSION = "1.24.3"

# Default token-processor pipeline with no optional extensions (identical order to upstream).
analyze_file = FileAnalyzer([
    preprocessing,
    comment_counter,
    line_counter,
    token_counter,
    condition_counter,
])

__all__ = ["analyze_file", "FileAnalyzer", "UPSTREAM_VERSION"]
