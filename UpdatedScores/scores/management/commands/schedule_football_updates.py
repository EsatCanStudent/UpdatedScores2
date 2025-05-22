from django.core.management.base import BaseCommand
import subprocess
import sys
import time
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = "Run all API-FOOTBALL data fetching commands in sequence with optimal scheduling"

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run in continuous mode with specified intervals',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Interval in seconds between update checks in continuous mode (default: 300)',
        )

    def handle(self, *args, **options):
        continuous = options.get('continuous', False)
        interval = options.get('interval', 300)
        
        if continuous:
            self.stdout.write(self.style.SUCCESS(f"Starting continuous update mode. Press Ctrl+C to stop."))
            self.continuous_mode(interval)
        else:
            self.stdout.write(self.style.SUCCESS("Running one-time update of all football data"))
            self.run_update_cycle()
    
    def continuous_mode(self, interval):
        """Run updates continuously with specified interval"""
        try:
            while True:
                # Get current time
                now = datetime.now()
                self.stdout.write(f"Update cycle starting at {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Run the update cycle
                self.run_update_cycle()
                
                # Calculate next run time
                next_run = datetime.now() + timedelta(seconds=interval)
                self.stdout.write(self.style.SUCCESS(f"Update complete. Next update at {next_run.strftime('%Y-%m-%d %H:%M:%S')}"))
                
                # Wait for the next cycle
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Update process stopped by user"))
            sys.exit(0)
    
    def run_update_cycle(self):
        """Run all the fetch commands in a logical order"""
        # Get current time to determine what to update
        now = datetime.now()
        hour = now.hour
        
        # Step 1: Always update matches (fetch upcoming and recent)
        self.run_command("fetch_api_football_matches", ["--last", "3", "--next", "7"])
        
        # Step 2: Update match previews
        # More aggressively before match days (morning and afternoon)
        days = 3 if 8 <= hour <= 14 else 2
        self.run_command("fetch_match_previews", ["--days", str(days)])
        
        # Step 3: Update lineups
        # Lineups are typically available 1 hour before the match
        self.run_command("fetch_match_lineups", ["--days", "1"])
        
        # Step 4: Update match events
        # We want frequent updates for live matches
        self.run_command("fetch_match_events", ["--days", "1"])
        
        # Step 5: Update match statistics
        # For completed matches
        self.run_command("fetch_match_statistics", ["--days", "2"])
    
    def run_command(self, command, args=None):
        """Run a Django management command and capture output"""
        cmd_args = [sys.executable, "manage.py", command]
        
        if args:
            cmd_args.extend(args)
        
        self.stdout.write(self.style.WARNING(f"Running: {' '.join(cmd_args)}"))
        
        try:
            # Use subprocess to run the command
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Print output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.stdout.write(output.strip())
            
            # Capture any errors
            rc = process.poll()
            if rc != 0:
                stderr = process.stderr.read()
                self.stdout.write(self.style.ERROR(f"Command failed with exit code {rc}"))
                self.stdout.write(self.style.ERROR(stderr))
            
            return rc == 0
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running {command}: {str(e)}"))
            return False
