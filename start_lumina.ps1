# Lumina RAG Agent - Quick Start Script
# This script starts the backend and opens the frontend

Write-Host "🤖 Starting Lumina RAG Agent..." -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

# Check if Python is available
Write-Host "`n1️⃣ Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✅ $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python not found! Install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check if dependencies are installed
Write-Host "`n2️⃣ Checking dependencies..." -ForegroundColor Yellow
$packages = @("flask", "langchain-groq", "langgraph")
$missing = @()

foreach ($package in $packages) {
    $check = pip show $package 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ $package installed" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $package missing" -ForegroundColor Red
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`n   💡 Installing missing packages..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Start the backend
Write-Host "`n3️⃣ Starting backend server..." -ForegroundColor Yellow
Write-Host "   🌐 Backend will run on http://localhost:5000" -ForegroundColor Cyan
Write-Host "   🔥 Powered by Groq + LangChain + LangGraph" -ForegroundColor Cyan
Write-Host "`n   Press CTRL+C to stop the server" -ForegroundColor Gray
Write-Host "=" * 60 -ForegroundColor Cyan

# Start backend in background
$backend = Start-Process -FilePath "python" -ArgumentList "lumina_backend.py" -PassThru -NoNewWindow

# Wait for backend to start
Write-Host "`n⏳ Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Test backend
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/api/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Backend is running!" -ForegroundColor Green
    Write-Host "   Status: $($health.status)" -ForegroundColor Cyan
} catch {
    Write-Host "⚠️ Backend may still be starting..." -ForegroundColor Yellow
}

# Open frontend
Write-Host "`n4️⃣ Opening frontend..." -ForegroundColor Yellow
$clientsPath = Join-Path $PSScriptRoot "public\clients.html"
Start-Process $clientsPath

Write-Host "`n🎉 Lumina is ready!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "`n📖 Quick Guide:" -ForegroundColor Yellow
Write-Host "   1. Look for the 💬 AI Chat button in the bottom-right" -ForegroundColor White
Write-Host "   2. Click it to open the chat window" -ForegroundColor White
Write-Host "   3. Try: 'Hello Lumina!' or 'Show vendors from UAE'" -ForegroundColor White
Write-Host "`n💡 Tips:" -ForegroundColor Yellow
Write-Host "   - Use ➕ to start a new conversation" -ForegroundColor White
Write-Host "   - Use 💬 to view conversation history" -ForegroundColor White
Write-Host "   - Use 💾 to export current chat" -ForegroundColor White
Write-Host "`n🛑 To stop: Press CTRL+C in this window" -ForegroundColor Gray
Write-Host "=" * 60 -ForegroundColor Cyan

# Keep script running
try {
    Wait-Process -Id $backend.Id
} catch {
    Write-Host "`n👋 Lumina backend stopped." -ForegroundColor Yellow
}
