import subprocess

res = subprocess.run(['pytest', 'tests/test_e2e_canonical.py', '-v', '-s'], capture_output=True, text=True)
with open('out_test.txt', 'w', encoding='utf-8') as f:
    f.write(res.stdout)
    f.write(res.stderr)
