Write-Host "=== Iniciando servidor TLS seguro ===" -ForegroundColor Cyan
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
python .\server_tls\server_tls.py
Write-Host "Servidor TLS finalizado." -ForegroundColor Yellow
pause
