import requests
html = requests.get('http://127.0.0.1:8000/').text
scripts = html[html.find('<script>'):html.find('</script>')]

# Check everything is present
for name, keyword in [
    ("showFileViewer", "showFileViewer"),
    ("viewer CSS", "viewer-modal"),
    ("view-file handler", ".view-file"),
    ("handleOfficerAction", "handleOfficerAction"),
    ("btn-approve", "btn-approve"),
    ("Processing btn state", "Processing..."),
]:
    found = keyword in html
    print(f"  {name}: {'OK' if found else 'MISSING!'}")

# Check for syntax errors by looking at common problems
lines = scripts.split('\n')
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    # Skip empty lines, comments, and template literals
    if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
        continue
    # Check for common syntax issues
    if stripped.count('(') != stripped.count(')'):
        # Might be in a string, let's check more carefully
        in_string = stripped.count("'") % 2 != 0 or stripped.count('"') % 2 != 0
        if not in_string:
            print(f"  WARNING: Line {i}: possible paren mismatch: {stripped[:80]}")

print(f"Script length: {len(scripts)} chars, {len(lines)} lines")
print(f"HTML OK" if "showFileViewer" in html and "handleOfficerAction" in html else "HTML ISSUE")
