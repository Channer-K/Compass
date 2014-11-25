"""
Some custom settings for this compass web application.

You can override any definitions accordingly.
"""

# Used by building the full URL in email templates.
DOMAIN = "172.26.184.26:8887"

# The following extensions of the uploaded files in replies are allowed.
CONTENT_TYPES = [
    'image/jpeg', 'image/png', 'image/bmp', 'image/gif',
    'text/plain', 'text/csv',
    'application/pdf',
    'application/msword', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/zip', 'application/x-gzip',
    'application/x-tar', 'application/x-rar-compressed'
]

# Specify a max value for the size of uploaded file
MAX_UPLOAD_SIZE = 1024*1024*20

SYSTEM_EMAIL = 'gengqiangle@pset.suntec.net'

# Set the audit operation time-out period in seconds.
Audit_TimeOut = 60*60*2

# Set the planned tasks time-out period in seconds.
Ntf_Before_While_Planning = 60*60*3

# Set the published or confirmed tasks time-out period in seconds.
Ntf_Before_While_PandC = 60*60*3

# Change the status of the published tasks to Publishing(a task status)
# when they will be in scheduled start time.
Chg_Before_While_Planning = 60*60
