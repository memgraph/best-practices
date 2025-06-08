#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime

def run_command(command, description):
    print("\n" + "="*80)
    print(f"Running {description}")
    print("="*80)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        duration = time.time() - start_time
        print(f"\nOutput:")
        print("-"*40)
        print(result.stdout)
        if result.stderr:
            print("\nWarnings/Errors:")
            print("-"*40)
            print(result.stderr)
        print(f"\nCompleted in {duration:.2f} seconds")
        return True
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"\nCommand failed after {duration:.2f} seconds")
        print("\nOutput:")
        print("-"*40)
        print(e.stdout)
        print("\nErrors:")
        print("-"*40)
        print(e.stderr)
        return False

def main():
    print(f"\nStarting IAM Demo at {datetime.now()}")
    print("="*80)
    
    steps = [
        ("python3 postgres_iam.py", "PostgreSQL Data Generation"),
        ("python3 create_indices.py", "Index Creation"),
        ("python3 memgraph_migrate.py", "Data Migration to Memgraph"),
        ("python3 permission_analysis.py", "Permission Analysis")
    ]
    
    overall_start = time.time()
    success = True
    
    for command, description in steps:
        if not run_command(command, description):
            print(f"\nError: {description} failed. Stopping execution.")
            success = False
            break
    
    overall_duration = time.time() - overall_start
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print(f"Total execution time: {overall_duration:.2f} seconds")
    print(f"Status: {'Success' if success else 'Failed'}")
    print("="*80)

if __name__ == "__main__":
    main() 
