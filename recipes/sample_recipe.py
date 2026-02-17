recipe = [
    # Go to preset 1 first
    {"action": "preset", "preset": 1, "wait": 20},

    # Slow pan right
    {
        "action": "move",
        "direction": "right",
        "speed": 100,
        "duration": 15
    },

    {"action": "wait", "duration": 1.5},

    # Slow zoom in
    {
        "action": "zoom",
        "direction": "in",
        "speed": 1,
        "duration": 8
    },

    {"action": "wait", "duration": 1.5},

    # Pan left slightly faster
    {
        "action": "move",
        "direction": "left",
        "speed": 10,
        "duration": 5
    },

    {"action": "wait", "duration": 1.5},

    # Zoom out
    {
        "action": "zoom",
        "direction": "out",
        "speed": 10,
        "duration": 8
    }
]
