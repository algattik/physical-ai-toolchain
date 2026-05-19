# syntax=docker/dockerfile:1
#
# Single image used by both compose services. ROS 2 Jazzy provides Python 3.12
# plus rclpy/sensor_msgs system packages; we layer the Python deps from
# pyproject.toml on top using pip.
FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-rclpy \
        ros-jazzy-sensor-msgs \
        ros-jazzy-rmw-cyclonedds-cpp \
        python3-pip \
        python3-opencv \
        python3-fastapi \
        python3-uvicorn \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

# Why these three are pip-installed instead of apt:
#   - pydantic: apt ships v1, we need v2.
#   - pyarrow: no apt package on Ubuntu 24.04.
#   - av:      no apt package on Ubuntu 24.04.
#
# Why --ignore-installed (load-bearing, do not remove):
# pydantic 2.x requires typing_extensions >= 4.12, but the base image's
# python3-fastapi (apt) pulls in python3-typing-extensions 4.10. Apt-installed
# wheels have no RECORD file, so pip refuses to uninstall the older copy
# ("Cannot uninstall ... no RECORD file") and aborts. --ignore-installed tells
# pip to skip the uninstall and write a fresh copy under /usr/local, which
# takes precedence on sys.path. The flag is harmless for pyarrow and av (no
# version conflict) but removing it breaks the pydantic install.
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed \
        "av==17.0.1" \
        "pyarrow==24.0.0" \
        "pydantic==2.13.4"

# Install the package itself.
RUN pip3 install --no-cache-dir --break-system-packages --no-deps -e .

EXPOSE 8080

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["python3", "-m", "uvicorn", "scene_aligner.aligner:app", "--host", "0.0.0.0", "--port", "8080"]
