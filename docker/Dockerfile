# syntax=docker/dockerfile:1.7
FROM ros:humble-ros-base-jammy

SHELL ["/bin/bash", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
ARG PX4_VERSION=v1.16.2
ARG INSTALL_TORCH_CUDA=false
ARG INSTALL_ULTRALYTICS=false
ARG UBUNTU_APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/ubuntu
ARG ROS2_APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG GIT_MIRROR_PREFIX=

ENV ROS_DISTRO=humble \
    PX4_HOME=/opt/PX4-Autopilot \
    DRI_WORKSPACE=/workspace \
    PIP_BREAK_SYSTEM_PACKAGES=1

RUN rm -f /etc/apt/apt.conf.d/docker-clean \
    && printf 'Acquire::Retries "10";\nAcquire::ForceIPv4 "true";\nAcquire::Queue-Mode "access";\nAcquire::http::Timeout "60";\nAcquire::https::Timeout "60";\nAcquire::http::Pipeline-Depth "0";\nAcquire::https::Pipeline-Depth "0";\n' \
      > /etc/apt/apt.conf.d/80-dri-retries \
    && sed -i \
      -e "s|http://archive.ubuntu.com/ubuntu|${UBUNTU_APT_MIRROR}|g" \
      -e "s|http://security.ubuntu.com/ubuntu|${UBUNTU_APT_MIRROR}|g" \
      /etc/apt/sources.list \
    && mapfile -t apt_source_files < <(find /etc/apt /usr/share/ros-apt-source \
        -maxdepth 3 -type f \( -name "*.list" -o -name "*.sources" \) 2>/dev/null) \
    && for source_file in "${apt_source_files[@]}"; do \
      sed -i \
        -e "s|http://packages.ros.org/ros2/ubuntu|${ROS2_APT_MIRROR}|g" \
        -e "s|https://packages.ros.org/ros2/ubuntu|${ROS2_APT_MIRROR}|g" \
        "${source_file}"; \
      if grep -q "ros2/ubuntu" "${source_file}"; then \
        sed -i \
          -e "s|^Types:.*|Types: deb|g" \
          -e "s|^deb-src |# deb-src disabled for ROS mirror |g" \
          "${source_file}"; \
      fi; \
    done \
    && grep -R "packages.ros.org/ros2/ubuntu" -n /etc/apt /usr/share/ros-apt-source 2>/dev/null && exit 1 || true

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    ca-certificates \
    ccache \
    cmake \
    curl \
    git \
    gnupg \
    iproute2 \
    lsb-release \
    mesa-utils \
    net-tools \
    ninja-build \
    python3-colcon-common-extensions \
    python3-dev \
    python3-numpy \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    tmux \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-rmw-fastrtps-cpp \
    ros-humble-robot-state-publisher \
    ros-humble-rviz2 \
    ros-humble-tf-transformations \
    ros-humble-vision-msgs \
    ros-humble-ros-gz-bridge \
    ros-humble-ros-gz-image \
    ros-humble-ros-gz-sim \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
      -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/gazebo-stable.list

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends gz-harmonic \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir -i "${PIP_INDEX_URL}" --upgrade pip setuptools wheel \
    && pip3 install --no-cache-dir -i "${PIP_INDEX_URL}" \
      fastapi \
      gymnasium \
      jinja2 \
      "numpy<2" \
      "opencv-python-headless<4.12" \
      pandas \
      pillow \
      pydantic \
      python-multipart \
      pyyaml \
      requests \
      scipy \
      shapely \
      uvicorn[standard]

RUN pip3 install --no-cache-dir -i "${PIP_INDEX_URL}" \
      argcomplete \
      empy==3.3.4 \
      jsonschema \
      kconfiglib \
      packaging \
      pyros-genmsg \
      toml \
      yamlargparse

RUN if [ "${INSTALL_TORCH_CUDA}" = "true" ]; then \
      pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121; \
    elif [ "${INSTALL_ULTRALYTICS}" = "true" ]; then \
      pip3 install --no-cache-dir -i "${PIP_INDEX_URL}" ultralytics; \
    fi

RUN git config --global http.version HTTP/1.1 \
    && git config --global http.postBuffer 524288000 \
    && for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --branch "${PX4_VERSION}" "${GIT_MIRROR_PREFIX}https://github.com/PX4/PX4-Autopilot.git" "${PX4_HOME}" && break; \
      rm -rf "${PX4_HOME}"; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep $((attempt * 15)); \
    done

RUN cd "${PX4_HOME}" \
    && if [ -n "${GIT_MIRROR_PREFIX}" ]; then \
      git config --global url."${GIT_MIRROR_PREFIX}https://github.com/".insteadOf https://github.com/; \
    fi \
    && git submodule sync --recursive \
    && required_submodules=( \
      Tools/simulation/gz \
      src/drivers/gps/devices \
      src/lib/cdrstream/cyclonedds \
      src/lib/cdrstream/rosidl \
      src/lib/crypto/libtomcrypt \
      src/lib/crypto/libtommath \
      src/lib/crypto/monocypher \
      src/lib/events/libevents \
      src/lib/heatshrink/heatshrink \
      src/modules/mavlink/mavlink \
      src/modules/uxrce_dds_client/Micro-XRCE-DDS-Client \
      src/modules/zenoh/zenoh-pico \
    ) \
    && verify_submodule() { \
      case "$1" in \
        Tools/simulation/gz) test -d "$1/models" ;; \
        src/lib/crypto/monocypher) test -f "$1/src/monocypher.c" ;; \
        src/lib/heatshrink/heatshrink) test -f "$1/heatshrink_decoder.c" ;; \
        src/modules/mavlink/mavlink) test -f "$1/message_definitions/v1.0/common.xml" ;; \
        src/modules/uxrce_dds_client/Micro-XRCE-DDS-Client) test -f "$1/CMakeLists.txt" ;; \
        *) test -d "$1" ;; \
      esac; \
    } \
    && clean_submodule() { \
      git submodule deinit -f "$1" || true; \
      rm -rf "$1" ".git/modules/$1"; \
      git submodule sync --recursive "$1"; \
    } \
    && update_one_submodule() { \
      local path="$1"; \
      for attempt in 1 2 3 4 5; do \
        echo "[PX4 submodule] ${path}, attempt ${attempt}"; \
        if git submodule update --init --recursive --depth 1 --jobs 1 "${path}" && verify_submodule "${path}"; then \
          return 0; \
        fi; \
        if git submodule update --init --recursive --jobs 1 "${path}" && verify_submodule "${path}"; then \
          return 0; \
        fi; \
        clean_submodule "${path}"; \
        sleep $((attempt * 10)); \
      done; \
      echo "[PX4 submodule] failed or incomplete: ${path}" >&2; \
      return 1; \
    } \
    && for submodule_path in "${required_submodules[@]}"; do \
      update_one_submodule "${submodule_path}"; \
    done \
    && test -f src/lib/heatshrink/heatshrink/heatshrink_decoder.c \
    && test -f src/lib/crypto/monocypher/src/monocypher.c \
    && test -f src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml \
    && git submodule status --recursive "${required_submodules[@]}"

RUN git config --global http.version HTTP/1.1 \
    && for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --branch v2.0.1 "${GIT_MIRROR_PREFIX}https://github.com/eProsima/Micro-CDR.git" /tmp/Micro-CDR && break; \
      rm -rf /tmp/Micro-CDR; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep $((attempt * 10)); \
    done \
    && cmake -S /tmp/Micro-CDR -B /tmp/Micro-CDR/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DUCDR_SUPERBUILD=OFF \
      -DUCDR_ISOLATED_INSTALL=OFF \
      -DBUILD_SHARED_LIBS=OFF \
      -DUCDR_PIC=ON \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build /tmp/Micro-CDR/build -j"$(nproc)" \
    && cmake --install /tmp/Micro-CDR/build \
    && ldconfig \
    && rm -rf /tmp/Micro-CDR \
    && test -f /usr/local/share/microcdr/cmake/microcdrConfig.cmake

RUN cd "${PX4_HOME}" \
    && (bash ./Tools/setup/ubuntu.sh --no-nuttx --no-sim-tools || true) \
    && make px4_sitl_default

RUN for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --branch release/1.16 "${GIT_MIRROR_PREFIX}https://github.com/PX4/px4_msgs.git" /tmp/px4_msgs && break; \
      rm -rf /tmp/px4_msgs; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep $((attempt * 10)); \
    done \
    && mkdir -p /opt/px4_ros2_ws/src \
    && cp -a /tmp/px4_msgs /opt/px4_ros2_ws/src/px4_msgs \
    && source /opt/ros/humble/setup.bash \
    && cd /opt/px4_ros2_ws \
    && colcon build --symlink-install \
    && rm -rf /tmp/px4_msgs

RUN git config --global http.version HTTP/1.1 \
    && git config --global http.postBuffer 524288000 \
    && if [ -n "${GIT_MIRROR_PREFIX}" ]; then \
      git config --global url."${GIT_MIRROR_PREFIX}https://github.com/".insteadOf https://github.com/; \
    fi \
    && for attempt in 1 2 3 4 5; do \
      git clone --depth 1 --branch v2.4.3 "${GIT_MIRROR_PREFIX}https://github.com/eProsima/Micro-XRCE-DDS-Agent.git" /tmp/Micro-XRCE-DDS-Agent && break; \
      rm -rf /tmp/Micro-XRCE-DDS-Agent; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep $((attempt * 10)); \
    done \
    && cd /tmp/Micro-XRCE-DDS-Agent \
    && mkdir build && cd build \
    && cmake .. \
      -DUAGENT_P2P_PROFILE=OFF \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
    && for attempt in 1 2 3 4 5; do \
      cmake --build . -j1 && break; \
      if [ "${attempt}" = "5" ]; then exit 1; fi; \
      sleep $((attempt * 15)); \
    done \
    && cmake --install . \
    && ldconfig \
    && rm -rf /tmp/Micro-XRCE-DDS-Agent

RUN pip3 install --no-cache-dir -i "${PIP_INDEX_URL}" "setuptools<80"

RUN test -x "${PX4_HOME}/build/px4_sitl_default/bin/px4" \
    && test -f /opt/px4_ros2_ws/install/setup.bash \
    && command -v MicroXRCEAgent

COPY docker/entrypoint.sh /ros_entrypoint_dri.sh
RUN chmod +x /ros_entrypoint_dri.sh \
    && echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc \
    && echo "[ -f /workspace/ros2_ws/install/setup.bash ] && source /workspace/ros2_ws/install/setup.bash" >> /root/.bashrc \
    && echo "[ -f /opt/px4_ros2_ws/install/setup.bash ] && source /opt/px4_ros2_ws/install/setup.bash" >> /root/.bashrc

ENTRYPOINT ["/ros_entrypoint_dri.sh"]
CMD ["bash"]
