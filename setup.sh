#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

ENV_FILE="backend/.env"
ENV_EXAMPLE="backend/.env.example"

if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$ENV_EXAMPLE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "✓ Created backend/.env from template."
  else
    echo "✗ backend/.env.example not found. Run from project root."
    exit 1
  fi
else
  echo "✓ backend/.env already exists."
fi

# sed in-place flag — differs on macOS
SED_IN_PLACE=(-i)
if [[ "$(uname)" == "Darwin" ]]; then
  SED_IN_PLACE=(-i "")
fi

# Replace DATABASE_URL for Docker
sed "${SED_IN_PLACE[@]}" \
  's|mssql+pyodbc://sa:YourPassword@localhost:1433/wealthflow?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes|mssql+pyodbc://sa:WealthFlow_2024!@mssql:1433/wealthflow?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes|' \
  "$ENV_FILE"
echo "✓ Configured DATABASE_URL for Docker."

# Replace REDIS_URL for Docker
sed "${SED_IN_PLACE[@]}" 's|redis://localhost:6379/0|redis://redis:6379/0|' "$ENV_FILE"
echo "✓ Configured REDIS_URL for Docker."

# Generate SECRET_KEY if placeholder
if grep -q 'SECRET_KEY=your-super-secret-key-here' "$ENV_FILE"; then
  KEY=$(openssl rand -hex 32)
  sed "${SED_IN_PLACE[@]}" "s|SECRET_KEY=your-super-secret-key-here|SECRET_KEY=$KEY|" "$ENV_FILE"
  echo "✓ Generated SECRET_KEY."
fi

# Generate TOKEN_ENCRYPTION_KEY if empty
if grep -q '^TOKEN_ENCRYPTION_KEY=$' "$ENV_FILE"; then
  KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
         python  -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || true)
  if [ -n "$KEY" ]; then
    sed "${SED_IN_PLACE[@]}" "s|^TOKEN_ENCRYPTION_KEY=$|TOKEN_ENCRYPTION_KEY=$KEY|" "$ENV_FILE"
    echo "✓ Generated TOKEN_ENCRYPTION_KEY."
  else
    echo "⚠ Could not generate TOKEN_ENCRYPTION_KEY. Install: pip install cryptography"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete! Run:"
echo "    docker compose up --build"
echo ""
echo "  Optional — enable AI chat:"
echo "    1. Get a free key at https://console.groq.com/keys"
echo "    2. Set LLM_API_KEY in backend/.env"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
