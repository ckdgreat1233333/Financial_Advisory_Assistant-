
# Make database.faiss_db importable by re-exporting FAISSDatabase
from .faiss_db import FAISSDatabase

# Also need to handle the other database imports used in other files
try:
    from database.db import *
except ImportError:
    pass
