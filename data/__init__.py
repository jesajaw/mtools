"""
data -- shared file loading/saving plus the in-memory workspace that makes tools chains possible

- loaders.py / savers.py: format-handling functions
- store.py: the shared in-memory "current data" workspace
- results.py: the uniform DataSet shape tools hand their results back in
"""


from . import loaders, savers, store, results
__all__ = ["loaders", "savers", "store", "results"]
