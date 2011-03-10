"""
Signals relating to Script Progress.
"""
from django.dispatch import Signal


# Sent just after a scriptProgress goes to the next step.s
script_progress = Signal(providing_args=["scriptProgress",])

# Sent just after  scriptProgress is completed.
script_progress_was_completed = Signal(providing_args=["scriptProgress",])

