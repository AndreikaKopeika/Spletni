# PowerShell script for .env setup

Write-Host "Setting up .env file..." -ForegroundColor Green

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "Warning: .env file already exists. Removing..." -ForegroundColor Yellow
    Remove-Item ".env"
}

# Check if env.example exists
if (Test-Path "env.example") {
    Write-Host "Copying env.example to .env..." -ForegroundColor Cyan
    Copy-Item "env.example" ".env"
    
    Write-Host "Applying default values..." -ForegroundColor Cyan
    
    # Read file content
    $content = Get-Content ".env" -Raw
    
    # Replace values
    $content = $content -replace 'your_secret_key_here_make_it_long_and_random', 'OhhhSoYouHackedSecretKey?WellGoAheadAndBreakMyApp!@#$%^&*()_+{}|:<>?[]\;'',./1234567890abcdef'
    $content = $content -replace 'sk-your_openai_api_key_here', 'NEW_OPENAI_API_KEY_HERE_REPLACE_THIS'
    $content = $content -replace 'your_developer_panel_password', 'admin123'
    
    # Write back
    Set-Content ".env" $content -NoNewline
    
    Write-Host "Success: .env file created with default values!" -ForegroundColor Green
    Write-Host "Note: Edit .env file if needed" -ForegroundColor Yellow
} else {
    Write-Host "Error: env.example file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Done!" -ForegroundColor Green
