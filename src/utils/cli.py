import sys


def get_year(default):
    """Resolve the season year a script should run against.

    A year passed as the first CLI argument takes priority -- this is
    how the orchestrator (run_pipeline.py) hands off a single
    user-entered year to every stage without prompting per-script.
    Run standalone with no argument, the script falls back to an
    interactive prompt so it stays usable on its own.
    """

    if len(sys.argv) > 1:

        try:
            return int(sys.argv[1])
        except ValueError:
            raise ValueError(
                f"Invalid year argument: {sys.argv[1]!r}"
            )

    entered = input(
        f"Enter season year [{default}]: "
    ).strip()

    return int(entered) if entered else default
