"""
Some custom settings for compass application.

You can override any definitions accordingly.
"""

#
DOMAIN = "172.26.184.26:8888"

# the pk of system adiministrator group
SA_GID = 2

# the pk for some specific status
FailureAudit_Status = 1
FailurePost_Status = 2
SuccessPost_Status = 7
WaitingForPost_Status = 4

# File is image, text, word, excel or zip package can be uploaded.
CONTENT_TYPES = [
    'image/jpeg', 'image/png', 'image/bmp', 'image/gif',
    'text/plain', 'text/csv',
    'application/pdf',
    'application/msword', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/zip', 'application/x-tar', 'application/x-rar-compressed',
    'application/x-gzip'
]

# Specify a max value for the size of uploaded file
MAX_UPLOAD_SIZE = 1024*1024*20

SYSTEM_EMAIL = 'gengqiangle@pset.suntec.net'

#
Audit_TimeOut = 60*60*2
#
Ntf_Before_While_Planning = 60*60*3
#
Ntf_Before_While_PandC = 60*60*3
