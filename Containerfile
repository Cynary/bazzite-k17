# Build context is created by experimental/bore-thinlto/prepare-image.sh.
ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-deck@sha256:050572c864322f567a223741922f70932d2a888f34f6b839f12e06ebd8e08f64
FROM ${BASE_IMAGE} AS applications
RUN sed -i '/^exclude=/d' /etc/dnf/repos.override.d/*.repo
# The build needs Fedora's Xwayland headers; the runtime keeps Bazzite's Xwayland.
RUN dnf5 versionlock delete xorg-x11-server-Xwayland
RUN dnf5 install -y gcc gcc-c++ git make cmake meson ninja-build nasm \
    qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel \
    SDL2-devel SDL2_ttf-devel openssl-devel opus-devel libva-devel libvdpau-devel \
    libdrm-devel vulkan-loader-devel vulkan-headers libshaderc-devel glslang-devel \
    lcms2-devel xxhash-devel libdav1d-devel wayland-devel wayland-protocols-devel \
    libX11-devel libxcb-devel nodejs npm python3 curl tar xz \
    libXdamage-devel libXcomposite-devel libXcursor-devel libXrender-devel libXext-devel \
    libXfixes-devel libXxf86vm-devel libXtst-devel libXres-devel libXmu-devel libXi-devel \
    libxkbcommon-devel libcap-devel pixman-devel systemd-devel libinput-devel luajit-devel catch-devel \
    libdisplay-info-devel libliftoff-devel libei-devel libdecor-devel pipewire-devel \
    xcb-util-wm-devel xcb-util-errors-devel xcb-util-renderutil-devel xcb-util-image-devel \
    xcb-util-keysyms-devel hwdata libseat-devel libXrandr-devel xorg-x11-server-Xwayland-devel \
    spirv-headers-devel spirv-tools-devel
RUN npm install --global --prefix /usr/lib/moonmachine-build-tools --cache /tmp/npm-cache pnpm@11.24.0
ENV PATH="/usr/lib/moonmachine-build-tools/bin:${PATH}"
COPY apps/sources.json apps/checkout.py /build-input/
COPY apps/patches/ /build-input/patches/
# Separate build processes from the logged-in user's process-kill shortcuts.
RUN mkdir -p /build /out /usr/lib/moonmachine /tmp/moonmachine-build-home \
    && chown 1001:1001 /build /out /usr/lib/moonmachine /tmp/moonmachine-build-home
USER 1001:1001
RUN python3 /build-input/checkout.py /build
COPY apps/ /build-input/
RUN bash /build-input/build.sh
FROM ${BASE_IMAGE}
ARG SOURCE_COMMIT=unknown
LABEL org.opencontainers.image.title="Moonmachine" \
      org.opencontainers.image.description="Experimental full kernel with K17 FRL/VRR, BORE 6.8.0 and ThinLTO; no AutoFDO" \
      io.cynary.k17.source-commit="${SOURCE_COMMIT}"
COPY files/ /
COPY channel/cosign.pub /etc/pki/containers/cynary-k17.pub
COPY channel/cynary-k17.yaml /etc/containers/registries.d/cynary-k17.yaml
COPY configure-signature-policy.py /tmp/k17-signature-policy.py
RUN python3 /tmp/k17-signature-policy.py && rm /tmp/k17-signature-policy.py
COPY rpms/ /tmp/k17-bore-rpms/
COPY verify-boot.sh /usr/libexec/k17-verify-bore
COPY install-image.sh /tmp/k17-bore-install.sh
RUN /tmp/k17-bore-install.sh && rm -rf /tmp/k17-bore-rpms /tmp/k17-bore-install.sh
COPY apps/ /tmp/moonmachine-apps/
COPY --from=applications --chown=0:0 /out/ /tmp/moonmachine-built/
RUN dnf5 install -y qt6-qtbase qt6-qtdeclarative qt6-qtsvg SDL2_ttf sdl2-compat \
    libdav1d libshaderc lcms2 xxhash-libs python3-gobject libsoup3
RUN python3 /tmp/moonmachine-apps/install.py && rm -rf /tmp/moonmachine-apps
# Preserve the scheduling capability carried by Bazzite's Gamescope package.
RUN setcap cap_sys_nice=eip /usr/bin/gamescope
COPY tests/test_app_setup.py /tmp/test_app_setup.py
RUN python3 /tmp/test_app_setup.py && rm /tmp/test_app_setup.py
RUN LD_LIBRARY_PATH=/usr/lib/moonmachine/moonlight/usr/lib:/usr/lib/moonmachine/moonlight/usr/lib64 \
    ldd /usr/lib/moonmachine/moonlight/usr/bin/moonlight > /tmp/moonlight-libraries \
    && cat /tmp/moonlight-libraries && ! grep -q 'not found' /tmp/moonlight-libraries \
    && rm /tmp/moonlight-libraries
RUN ldd /usr/bin/gamescope > /tmp/gamescope-libraries \
    && cat /tmp/gamescope-libraries && ! grep -q 'not found' /tmp/gamescope-libraries \
    && rm /tmp/gamescope-libraries
RUN dnf5 clean all && rm -rf /var/cache/libdnf5 /var/cache/ldconfig/aux-cache /var/lib/dnf/repos && rm -f /var/log/dnf5.log
RUN --mount=type=tmpfs,target=/run --network=none bootc container lint
LABEL org.opencontainers.image.source="https://github.com/Cynary/bazzite-k17" \
      io.cynary.k17.release="moonmachine-20260922.3"
