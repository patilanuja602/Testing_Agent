# NOTE (Unit Testing Platform): this file was MODIFIED from the upstream Lizard 1.24.3 source.
# Upstream also exports the XML/CSV/HTML/Checkstyle report writers here; those are command-line
# output features that this application does not use and are not shipped.
# See third_party/lizard/MODIFICATIONS.md.
""" extensions of lizard """

from .auto_open import auto_open, auto_read
