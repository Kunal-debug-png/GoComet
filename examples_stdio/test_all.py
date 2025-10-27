#!/usr/bin/env python3
"""Test all MCP stdio servers"""
import subprocess
import sys
import os
from pathlib import Path

def test_server(name, command):
    """Test a single server"""
    print(f"\n[{name}] Testing...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  ✓ {name} working")
            return True
        else:
            print(f"  ✗ {name} failed (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"  ✗ {name} failed: {str(e)}")
        return False

def main():
    print("\n" + "="*50)
    print("Testing All MCP Stdio Servers")
    print("="*50)
    
    os.chdir(Path(__file__).parent)
    
    tests = [
        ("SQL Server", "type sql\\last_4_weeks.json | python ..\\app\\mcp\\servers\\srv_sql_stdio.py"),
        ("Pandas Server", "type pandas\\head_3.json | python ..\\app\\mcp\\servers\\srv_pandas_stdio.py"),
        ("Plotly Server", "python plotly\\line_chart.py"),
        ("Tracking Server", "type tracking\\create_new.json | python ..\\app\\mcp\\servers\\srv_tracking_stdio.py"),
        ("FileSystem Server", "type fs\\read_csv.json | python ..\\app\\mcp\\servers\\srv_fs_stdio.py"),
    ]
    
    results = []
    for name, command in tests:
        results.append(test_server(name, command))
    
    # Summary
    print("\n" + "="*50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All {total} servers working!")
    else:
        print(f"✗ {total - passed} server(s) failed ({passed}/{total} passed)")
    print("="*50 + "\n")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
