"""Motion profile library for cam design.

Importing this subpackage triggers registration of all motion profiles.
"""

# Import all profile modules so @register decorators execute
from . import cycloidal
from . import harmonic
from . import modified_sine
from . import polynomial345
from . import constant_velocity
