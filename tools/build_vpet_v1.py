"""Legacy-named compatibility entry point for the animation-master workflow.

Platform packaging is intentionally deferred until every independent master
action GIF has been reviewed.
"""

from build_action_gifs import build


if __name__ == "__main__":
    print("Legacy V1 entry point: building platform-neutral animation-master GIFs.")
    build()
