"""Standalone test for motion profile math (no FreeCAD dependency)."""

import sys
import os
import math

# Add parent to path so we can import fccamtrax.motion
sys.path.insert(0, os.path.dirname(__file__))

from fccamtrax.motion.cycloidal import Cycloidal
from fccamtrax.motion.harmonic import Harmonic
from fccamtrax.motion.modified_sine import ModifiedSine
from fccamtrax.motion.polynomial345 import Polynomial345
from fccamtrax.motion.constant_velocity import ConstantVelocity


def test_profile(profile, name):
    """Test a motion profile for boundary conditions and monotonicity."""
    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"{'='*50}")

    # Boundary conditions
    s0 = profile.displacement(0.0)
    s1 = profile.displacement(1.0)
    print(f"  s(0) = {s0:.6f}  (expected 0.0)")
    print(f"  s(1) = {s1:.6f}  (expected 1.0)")
    assert abs(s0) < 1e-6, f"s(0) should be 0, got {s0}"
    assert abs(s1 - 1.0) < 1e-6, f"s(1) should be 1, got {s1}"

    # Monotonicity check (displacement should be non-decreasing)
    prev = 0.0
    monotonic = True
    for i in range(1, 101):
        t = i / 100.0
        s = profile.displacement(t)
        if s < prev - 1e-10:
            monotonic = False
            print(f"  WARNING: s({t:.2f}) = {s:.6f} < s({(i-1)/100:.2f}) = {prev:.6f}")
        prev = s
    print(f"  Monotonic: {monotonic}")

    # Sample values
    samples = [0.0, 0.25, 0.5, 0.75, 1.0]
    print(f"\n  {'t':>6}  {'s':>10}  {'v':>10}  {'a':>10}  {'j':>10}")
    for t in samples:
        s = profile.displacement(t)
        v = profile.velocity(t)
        a = profile.acceleration(t)
        j = profile.jerk(t)
        print(f"  {t:6.2f}  {s:10.6f}  {v:10.6f}  {a:10.6f}  {j:10.6f}")


def main():
    profiles = [
        (Cycloidal(), "Cycloidal"),
        (Harmonic(), "Harmonic"),
        (ModifiedSine(), "Modified Sine"),
        (Polynomial345(), "3-4-5 Polynomial"),
        (ConstantVelocity(), "Constant Velocity"),
    ]

    all_passed = True
    for profile, name in profiles:
        try:
            test_profile(profile, name)
        except AssertionError as e:
            print(f"  FAILED: {e}")
            all_passed = False

    print(f"\n{'='*50}")
    print(f"Result: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
