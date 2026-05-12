"""Local development helpers — NOT part of the deployed scene-aligner.

This is a separate top-level package, deliberately *not* nested under
``scene_aligner``, to make it impossible to import these modules through
the production package's namespace and to let packaging tools include or
exclude them as one unit.

The production wheel built from this repository ships ``scene_aligner``
only; ``scene_aligner_dev`` lives in the source tree and is installed
via the ``[project.optional-dependencies] dev`` extra (``pip install
.[dev]``) or any editable install used by the docker-compose setup.

Currently provides:
    * ``scene_aligner_dev.fake_camera`` — replays a recorded dataset's
      videos onto the ROS 2 camera topics the aligner is subscribed to.
"""
