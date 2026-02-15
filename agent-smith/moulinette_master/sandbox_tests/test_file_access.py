# Test: File access restrictions - copy/paste entire file at once

# Test /etc/passwd - should fail
try:
    f = open('/etc/passwd', 'r')
    f.close()
    print("FAIL: /etc/passwd accessible")
except PermissionError:
    print("OK: /etc/passwd blocked")

# Test path traversal - should fail
try:
    f = open('../../../etc/passwd', 'r')
    f.close()
    print("FAIL: path traversal accessible")
except PermissionError:
    print("OK: path traversal blocked")

# Test /home - should fail
try:
    f = open('/home/user/.bashrc', 'r')
    f.close()
    print("FAIL: /home accessible")
except PermissionError:
    print("OK: /home blocked")

# Test /root - should fail
try:
    f = open('/root/.bashrc', 'r')
    f.close()
    print("FAIL: /root accessible")
except PermissionError:
    print("OK: /root blocked")

print("=== FILE ACCESS TEST COMPLETE ===")
