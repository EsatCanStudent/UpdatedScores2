# UpdatedScores API-FOOTBALL Scheduler Setup Script
# This script sets up a scheduled task to run the API-FOOTBALL data updates at regular intervals

# Configuration
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = "python"  # Assumes python is in PATH, update this if needed
$taskName = "UpdatedScores_API_Football_Updates"
$taskDescription = "Fetches and updates football data from API-FOOTBALL"
$logPath = Join-Path $projectPath "logs"
$logFile = Join-Path $logPath "api_football_updates.log"

# Create log directory if it doesn't exist
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath | Out-Null
    Write-Host "Created log directory: $logPath"
}

# Define the script that will be executed by the scheduled task
$scriptContent = @"
# Scheduled task script for API-FOOTBALL updates
cd '$projectPath'
`$env:PYTHONPATH='$projectPath'

# Get current date/time for logging
`$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path '$logFile' -Value "`$timestamp - Starting API-FOOTBALL update"

try {
    # Run the schedule_football_updates command
    & '$pythonPath' manage.py schedule_football_updates 2>&1 | Tee-Object -FilePath '$logFile' -Append
    
    # Log completion
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path '$logFile' -Value "`$timestamp - API-FOOTBALL update completed successfully"
} catch {
    # Log error
    `$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss" 
    Add-Content -Path '$logFile' -Value "`$timestamp - ERROR: `$_"
}
"@

# Save the script to a file
$scriptPath = Join-Path $projectPath "run_api_football_updates.ps1"
Set-Content -Path $scriptPath -Value $scriptContent
Write-Host "Created task script: $scriptPath"

# Create a scheduled task
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "Task '$taskName' already exists. Removing existing task..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the scheduled task action
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# Create trigger (run every 30 minutes)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Days 3650)

# Register the task
Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Action $action -Trigger $trigger -RunLevel Highest

Write-Host "Scheduled task '$taskName' has been created."
Write-Host "Task will run every 30 minutes and update football data from API-FOOTBALL."
Write-Host "Logs will be saved to: $logFile"
Write-Host 
Write-Host "You can also run updates manually using:"
Write-Host "python manage.py schedule_football_updates"
Write-Host 
Write-Host "To fetch specific data types, use these commands:"
Write-Host "- python manage.py fetch_api_football_matches"
Write-Host "- python manage.py fetch_match_lineups"
Write-Host "- python manage.py fetch_match_events"
Write-Host "- python manage.py fetch_match_statistics"
Write-Host "- python manage.py fetch_match_previews"