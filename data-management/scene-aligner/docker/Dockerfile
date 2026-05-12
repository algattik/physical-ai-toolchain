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
        python3-pip \
        python3-opencv \
        python3-fastapi \
        python3-uvicorn \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml /app/
COPY src/ /app/src/

# pydantic v2 (apt ships v1) and pyarrow (no apt package on Ubuntu 24.04).
# typing_extensions is apt-installed and pip can't uninstall it; use
# --ignore-installed so pip overlays a newer copy in /usr/local.
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed \
        "pyarrow==24.0.0" \
        "pydantic==2.13.4"

# Install the package itself.
RUN pip3 install --no-cache-dir --break-system-packages --no-deps -e .

EXPOSE 8080

# ros entrypoint sources /opt/ros/jazzy/setup.bash; commands come from compose.
