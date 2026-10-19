"""
data -- shared file loading/saving plus the in-memory workspace that makes tools chains possible

- loaders.py / savers.py: format-handling functions
- store.py: the shared in-memory "current data" workspace
- results.py: the uniform DataSet shape tools hand their results back in
- session.py: the GUI-free load/save workflow shared by the main window and all tool windows
"""


from . import loaders, savers, store, results, session
__all__ = ["loaders", "savers", "store", "results", "session"]
