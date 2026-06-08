FAULT_CLASSES = [
    "person_on_track",
    "foreign_object",
    "rock_or_debris",
    "fallen_branch",
    "fastener_missing",
    "fastener_broken",
    "rail_surface_defect",
    "sleeper_or_slab_damage",
    "fence_intrusion_damage",
    "catenary_or_pole_abnormal",
]

SEVERITY_BY_CLASS = {
    "person_on_track": "critical",
    "foreign_object": "high",
    "rock_or_debris": "high",
    "fallen_branch": "high",
    "fastener_missing": "medium",
    "fastener_broken": "medium",
    "rail_surface_defect": "medium",
    "sleeper_or_slab_damage": "medium",
    "fence_intrusion_damage": "medium",
    "catenary_or_pole_abnormal": "high",
}

CLASS_COLORS_BGR = {
    "person_on_track": (60, 20, 220),
    "foreign_object": (0, 140, 255),
    "rock_or_debris": (90, 90, 90),
    "fallen_branch": (30, 120, 60),
    "fastener_missing": (40, 40, 40),
    "fastener_broken": (30, 30, 180),
    "rail_surface_defect": (180, 60, 60),
    "sleeper_or_slab_damage": (180, 160, 60),
    "fence_intrusion_damage": (200, 80, 160),
    "catenary_or_pole_abnormal": (20, 200, 220),
}
