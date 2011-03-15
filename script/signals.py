"""
Signals relating to Script Progress.
"""
from django.dispatch import Signal


# Sent just after a scriptProgress goes to the next step.
script_progress = Signal(providing_args=["connection","step"])

# Sent just after a scriptProgress goes to the next step.
script_progress_pre_change=Signal(providing_args=["connection","step"])

# Sent just after  scriptProgress is completed.
script_progress_was_completed = Signal(providing_args=["connection",])


