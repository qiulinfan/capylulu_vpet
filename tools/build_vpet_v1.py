"""Compatibility entry point for the current animation-first workflow.

Whole-pet atlas assembly is intentionally deferred until every independent
action GIF has been reviewed.
"""

from build_action_gifs import build


if __name__ == "__main__":
    print("Whole-pet atlas assembly is deferred; building independent action GIFs instead.")
    build()
