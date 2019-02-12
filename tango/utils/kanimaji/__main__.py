import sys

from . import create_gif

for arg in sys.argv[1:]:
    create_gif(arg)
