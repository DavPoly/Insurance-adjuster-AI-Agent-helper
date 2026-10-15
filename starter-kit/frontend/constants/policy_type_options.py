from enum import Enum


class PolicyTypeOption(str, Enum):
    BASIC_HOMEOWNER = "basic_homeowner"
    STANDARD_HOMEOWNER = "standard_homeowner"
    PREMIUM_HOMEOWNER = "premium_homeowner"
    RENTERS = "renters"
    LANDLORD = "landlord"


DEFAULT_POLICY_TYPE_OPTION = PolicyTypeOption.STANDARD_HOMEOWNER
POLICY_TYPE_SETTING_WIDGET_ID = "policy_type"
