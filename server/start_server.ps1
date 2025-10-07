# PowerShell script for Windows
.\..\\.venv\Scripts\Activate.ps1
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = 1
python -m flask run --host=0.0.0.0 --port=3001
