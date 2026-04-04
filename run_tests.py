#!/usr/bin/env python
"""Run backend tests for story 2-2"""
import subprocess
import sys
import os

os.chdir('d:\\code\\ai-class')

print("=" * 70)
print("TEST 1: Story 2-2 Specific Test Files")
print("=" * 70)

cmd1 = [
    sys.executable, '-m', 'pytest',
    'backend/tests/test_validate_hint_nodes.py',
    'backend/tests/test_chat_sse.py',
    'backend/tests/test_graph_state.py',
    '-q'
]

result1 = subprocess.run(cmd1)

print("\n" + "=" * 70)
print("TEST 2: All Backend Tests")
print("=" * 70)

cmd2 = [sys.executable, '-m', 'pytest', 'backend/tests', '-q']

result2 = subprocess.run(cmd2)

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Test 1 (Specific files): {'PASSED' if result1.returncode == 0 else 'FAILED'}")
print(f"Test 2 (All backend): {'PASSED' if result2.returncode == 0 else 'FAILED'}")

sys.exit(max(result1.returncode, result2.returncode))
