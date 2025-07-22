# deploy.ps1

# Zatrzymaj skrypt, jeśli wystąpi błąd
$ErrorActionPreference = "Stop"

Write-Host "`n[1/5] Dodawanie zmian do GIT..."
git add .

Write-Host "[2/5] Commit zmian..."
git commit -m "Aktualizacja kodu"

Write-Host "[3/5] Push do GitHuba..."
git push

Write-Host "[4/5] Łączenie z VM i pull + Docker build/up..."
az ssh vm --ip 10.0.11.5 --command @"
sudo git -C /docker/build-files/andon-signals pull
cd /docker/compose-signals
sudo docker compose build
sudo docker compose up -d
"@

Write-Host "`n✅ Gotowe. Kod został wdrożony!"
