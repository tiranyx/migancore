#!/usr/bin/env python3
"""Apply CSP header to all nginx configs."""
import re

CONFIGS = [
    "/www/server/panel/vhost/nginx/app.migancore.com.conf",
    "/www/server/panel/vhost/nginx/migancore.com.conf",
]

CSP_LINE = '    add_header Content-Security-Policy "default-src \'self\'; script-src \'self\' \'unsafe-inline\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data: blob:; connect-src \'self\'; font-src \'self\'; frame-ancestors \'none\'; base-uri \'self\'; form-action \'self\'" always;\n'

for path in CONFIGS:
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Skip: {path} not found")
        continue

    # Remove any existing CSP lines
    content = re.sub(r'\s*# Content-Security-Policy.*?\n', '\n', content)
    content = re.sub(r'\s*add_header Content-Security-Policy.*?\n', '\n', content)

    # Insert CSP after Strict-Transport-Security header (if exists)
    if 'add_header Strict-Transport-Security' in content:
        content = content.replace(
            'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
            'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n' + CSP_LINE
        )
    else:
        # Insert after X-Frame-Options
        content = content.replace(
            'add_header X-Frame-Options "SAMEORIGIN" always;',
            'add_header X-Frame-Options "SAMEORIGIN" always;\n' + CSP_LINE
        )

    with open(path, "w") as f:
        f.write(content)

    print(f"CSP applied to {path}")
