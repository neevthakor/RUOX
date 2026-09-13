from enum import IntEnum, Enum

class PermissionLevel(IntEnum):
    READ = 1
    LOW_RISK = 2
    MEDIUM_RISK = 3
    HIGH_RISK = 4
    CRITICAL = 5

class PrivacyClass(Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    PRIVATE = "PRIVATE"
    SENSITIVE = "SENSITIVE"
    SECRET = "SECRET"

class SecurityState:
    def __init__(self):
        self.local_only_mode = True
        self.computer_control_enabled = True
        self.internet_enabled = False
        
    def disable_computer_control(self):
        self.computer_control_enabled = False
        
    def enable_computer_control(self):
        self.computer_control_enabled = True

# Global singleton for emergency overrides
global_security_state = SecurityState()
