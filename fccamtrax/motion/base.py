"""Base class for all cam motion profiles.

All motion profiles operate on normalized parameters:
  - t in [0, 1]: normalized cam angle (0 = start of motion, 1 = end)
  - output in [0, 1]: normalized displacement
  - velocity, acceleration, jerk: derivatives w.r.t. normalized time
"""

import math
from abc import ABC, abstractmethod


class MotionProfile(ABC):
    """Abstract base class for cam motion profiles.

    Subclasses must implement displacement(t). Default velocity/acceleration/jerk
    use analytical derivatives where possible, numerical differentiation otherwise.
    """

    @abstractmethod
    def displacement(self, t: float) -> float:
        """Normalized displacement at normalized angle t. Returns [0, 1]."""
        ...

    def velocity(self, t: float) -> float:
        """First derivative (velocity) at t. Analytical if available, else numerical."""
        return self._numerical_derivative(t, self.displacement, order=1)

    def acceleration(self, t: float) -> float:
        """Second derivative (acceleration) at t."""
        return self._numerical_derivative(t, self.displacement, order=2)

    def jerk(self, t: float) -> float:
        """Third derivative (jerk/pulse) at t."""
        return self._numerical_derivative(t, self.displacement, order=3)

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g., 'Cycloidal', 'Harmonic')."""
        ...

    @property
    def category(self) -> str:
        """Category: 'standard', 'polynomial', 'custom'."""
        return "standard"

    @property
    def params(self) -> dict:
        """Adjustable parameters for this profile."""
        return {}

    @params.setter
    def params(self, d: dict):
        pass

    def _numerical_derivative(self, t: float, func, order: int = 1, dt: float = 1e-6) -> float:
        """Numerical nth derivative using central differences."""
        if order == 1:
            return (func(t + dt) - func(t - dt)) / (2 * dt)
        elif order == 2:
            return (func(t + dt) - 2 * func(t) + func(t - dt)) / (dt * dt)
        elif order == 3:
            return (func(t + 2*dt) - 2*func(t + dt) + 2*func(t - dt) - func(t - 2*dt)) / (2 * dt**3)
        else:
            raise ValueError(f"Unsupported derivative order: {order}")
