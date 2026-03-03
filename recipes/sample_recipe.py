recipe = [

    {"action": "preset", "preset": 1, "wait": 10},

    # Slow diagonal sweep
    {
    "action": "move_diagonal",
    "pan": 0.4,
    "tilt": -0.2,
    "duration": 10
    },

    {"action": "wait", "duration": 2},

    # Pure tilt up
    {
        "action": "move",
        "pan": 0.0,
        "tilt": 0.25,
        "duration": 3
    },

    {"action": "wait", "duration": 1},

    # Pan + tilt opposite diagonal
    {
        "action": "move",
        "pan": -0.4,
        "tilt": -0.2,
        "duration": 4
    }
]
