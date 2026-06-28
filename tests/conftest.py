import os

# Config._require() runs at class definition time, so SECRET_KEY must be in the
# environment before any `import app.*` happens during test collection.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
