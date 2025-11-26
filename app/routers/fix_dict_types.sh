#!/bin/bash
# Script de correction des types de retour Dict

cd ~/LaHotte-Back/app/routers

echo "🔧 Suppression des types de retour Dict qui causent des problèmes..."

# Backup
backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"
cp *.py "$backup_dir/"
echo "📦 Backup créé dans $backup_dir/"

# Correction auth.py
sed -i 's/def logout(response: Response) -> Dict\[str, str\]:/def logout(response: Response):/' auth.py

# Correction familles.py
sed -i 's/) -> Dict\[str, str\]:/:/' familles.py
sed -i 's/) -> Dict\[str, Any\]:/:/' familles.py

echo "✅ Corrections terminées!"
