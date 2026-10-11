from . import overpowered, redundant, repeated_prompt

# (config section, detector module)
DETECTORS = [
    ("overpowered_model", overpowered),
    ("repeated_prompt", repeated_prompt),
    ("redundant_calls", redundant),
]
