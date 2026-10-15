"""Enumerated claim classification values shared by the triage agent's tool
schemas and its final assessment, matching api-contract/openapi.yaml exactly.
"""

from enum import Enum


class DamageType(str, Enum):
    WATER_DAMAGE = "water_damage"
    FIRE_DAMAGE = "fire_damage"
    STORM_DAMAGE = "storm_damage"
    BREAK_IN = "break_in"
    VANDALISM = "vandalism"
    OTHER = "other"


class SeverityLevel(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CATASTROPHIC = "catastrophic"


class PolicyType(str, Enum):
    BASIC_HOMEOWNER = "basic_homeowner"
    STANDARD_HOMEOWNER = "standard_homeowner"
    PREMIUM_HOMEOWNER = "premium_homeowner"
    RENTERS = "renters"
    LANDLORD = "landlord"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
