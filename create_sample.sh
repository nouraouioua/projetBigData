#!/bin/bash
# Créer un échantillon réduit du dataset pour économiser l'espace disque

DATA_DIR="data"
FULL_FILE="$DATA_DIR/NASA_access_log_full.txt"
SAMPLE_FILE="$DATA_DIR/NASA_access_log_sample.txt"

# Prendre seulement les 500 000 premières lignes (~10% du dataset)
echo "Creation d'un echantillon reduit du dataset..."
head -n 500000 "$FULL_FILE" > "$SAMPLE_FILE"

echo "Echantillon cree: $SAMPLE_FILE"
ls -lh "$SAMPLE_FILE"
