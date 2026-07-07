param()

$ErrorActionPreference = "Stop"

$envFile = "backend\.env"
$envExample = "backend\.env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "✓ Created backend\.env from template."
    } else {
        Write-Error "✗ backend\.env.example not found. Run from project root."
        exit 1
    }
} else {
    Write-Host "✓ backend\.env already exists."
}

# Read content
$content = [System.IO.File]::ReadAllText((Resolve-Path $envFile))

# Replace DATABASE_URL with Docker values
$content = $content.Replace(
    'DATABASE_URL=mssql+pyodbc://sa:YourPassword@localhost:1433/wealthflow?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes',
    'DATABASE_URL=mssql+pyodbc://sa:WealthFlow_2024!@mssql:1433/wealthflow?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes'
)
Write-Host "✓ Configured DATABASE_URL for Docker."

# Replace REDIS_URL with Docker values
$content = $content.Replace(
    'REDIS_URL=redis://localhost:6379/0',
    'REDIS_URL=redis://redis:6379/0'
)
Write-Host "✓ Configured REDIS_URL for Docker."

# Generate SECRET_KEY if still placeholder
if ($content.Contains('SECRET_KEY=your-super-secret-key-here')) {
    $key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    $content = $content.Replace('SECRET_KEY=your-super-secret-key-here', "SECRET_KEY=$key")
    Write-Host "✓ Generated SECRET_KEY."
}

# Generate TOKEN_ENCRYPTION_KEY if empty (Fernet = urlsafe_b64encode(32 random bytes))
if ($content.Contains('TOKEN_ENCRYPTION_KEY=')) {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $key = [Convert]::ToBase64String($bytes) -replace '\+', '-' -replace '/', '_' -replace '=', ''
    $content = $content.Replace("TOKEN_ENCRYPTION_KEY=", "TOKEN_ENCRYPTION_KEY=$key")
    Write-Host "✓ Generated TOKEN_ENCRYPTION_KEY."
}

[System.IO.File]::WriteAllText((Resolve-Path $envFile), $content)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Setup complete! Run:"
Write-Host "    docker compose up --build"
Write-Host ""
Write-Host "  Optional — enable AI chat:"
Write-Host "    1. Get a free key at https://console.groq.com/keys"
Write-Host "    2. Set LLM_API_KEY in backend\.env"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
