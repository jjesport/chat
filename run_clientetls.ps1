Write-Host "=== Iniciando cliente TLS seguro ===" -ForegroundColor Cyan
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
python .\server_tls\cliente_tls.py
Write-Host "Cliente TLS finalizado." -ForegroundColor Yellow
pause