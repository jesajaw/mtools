"""
data -- shared file loading/saving plus the in-memory workspace
(store.py) that lets tools chain: run AFM Geometry, then feed its
output straight into an analysis tool, without saving/reloading a
file in between.

Not under tools/: infrastructure, not a "topic" category for
core.registry to discover. Deliberately not named `io` either --
that would shadow the stdlib io module.

- loaders.py / savers.py: format-handling functions.
- store.py: the shared in-memory "current data" workspace.
"""
