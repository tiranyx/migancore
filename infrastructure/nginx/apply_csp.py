#!/usr/bin/env python3
"""Apply CSP header to nginx config."""
import re

CONFIG_PATH = "/www/server/panel/vhost/nginx/api.migancore.com.conf"
CSP_LINE = '    add_header Content-Security-Policy "default-src \'self\'; script-src \'self\' \'unsafe-inline\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data: blob:; connect-src \'self\'; font-src \'self\'; frame-ancestors \'none\'; base-uri \'self\'; form-action \'self\'" always;\n'

with open(CONFIG_PATH, "r") as f:
    content = f.read()

# Remove any existing CSP lines
content = re.sub(r'\s*# Content-Security-Policy.*?\n', '\n', content)
content = re.sub(r'\s*add_header Content-Security-Policy.*?\n', '\n', content)

# Insert CSP after Strict-Transport-Security header
content = content.replace(
    'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
    'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n' + CSP_LINE
)

with open(CONFIG_PATH, "w") as f:
    f.write(content)

print("CSP header applied.")
