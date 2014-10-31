"""
Some custom settings for compass application.

You can override any definations accordingly.
"""

# the pk of system adiministrator group
SA_GROUP_ID = 2
SA_LEADER_RID = 2

# the keyword contained the name of leader role
LEADER_STR = "leader"

# the pk for some specific status
FailureAudit_STATUS = 1
FailurePost_STATUS = 2
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
MAX_UPLOAD_SIZE = 1024*1024*10

SYSTEM_EMAIL = '#'

SCHEDULE_PERIOD = 20*60
