"""Motion profile registry for dynamic lookup and extension."""

from __future__ import annotations
from typing import Type

from .base import MotionProfile

_profile_registry: dict[str, Type[MotionProfile]] = {}


def register(cls: Type[MotionProfile]) -> Type[MotionProfile]:
    """Decorator to register a motion profile class.

    Usage:
        @register
        class MyProfile(MotionProfile):
            ...
    """
    _profile_registry[cls.__name__] = cls
    return cls


# Import profile modules after register() is defined so their @register works
from . import cycloidal
from . import harmonic
from . import modified_sine
from . import polynomial345
from . import constant_velocity


def get(name: str) -> MotionProfile:
    """Get a motion profile instance by class name or display name."""
    if name in _profile_registry:
        return _profile_registry[name]()
    for cls in _profile_registry.values():
        inst = cls()
        if inst.name == name:
            return inst
    raise KeyError(f"Unknown motion profile: {name}")


def list_all() -> list[str]:
    """List all registered motion profile display names."""
    return [cls().name for cls in _profile_registry.values()]


def list_by_category(category: str) -> list[str]:
    """List profile names filtered by category."""
    return [cls().name for cls in _profile_registry.values()
            if cls().category == category]
