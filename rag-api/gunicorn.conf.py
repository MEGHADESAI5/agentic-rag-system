import os
import multiprocessing

# Force a single worker to drastically reduce memory usage
workers = 1

# Use threads instead of processes for concurrency to save memory
threads = 2

# Bind to the port Render provides
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Timeout to prevent hanging
timeout = 120