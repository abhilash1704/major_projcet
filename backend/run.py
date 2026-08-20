import os
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

# Disable multi-threading in C-level linear algebra libraries to prevent thread exhaustion
# and silent crashes when called from Werkzeug's multiple HTTP request threads.
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
