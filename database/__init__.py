
# Make database.faiss_db importable by re-exporting FAISSDatabase.
# Imported lazily so that pure-Python modules can be imported and tested
# without requiring the optional faiss-cpu dependency.
def FAISSDatabase(*args, **kwargs):
    from .faiss_db import FAISSDatabase as _FAISSDatabase
    return _FAISSDatabase(*args, **kwargs)

# Also need to handle the other database imports used in other files
try:
    from database.db import *
except ImportError:
    pass
