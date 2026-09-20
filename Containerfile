# Build context is created by experimental/bore-thinlto/prepare-image.sh.
ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-deck@sha256:050572c864322f567a223741922f70932d2a888f34f6b839f12e06ebd8e08f64
FROM ${BASE_IMAGE} AS applications
RUN sed -i '/^exclude=/d' /etc/dnf/repos.override.d/*.repo
RUN dnf5 install -y gcc gcc-c++ git make cmake meson ninja-build nasm \
    qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel \
    SDL2-devel SDL2_ttf-devel openssl-devel opus-devel libva-devel libvdpau-devel \
    libdrm-devel vulkan-loader-devel vulkan-headers libshaderc-devel glslang-devel \
    lcms2-devel xxhash-devel libdav1d-devel wayland-devel wayland-protocols-devel \
    libX11-devel libxcb-devel nodejs npm python3 curl tar xz
RUN npm install --global --prefix /usr/lib/moonmachine-build-tools --cache /tmp/npm-cache pnpm@11.24.0
ENV PATH="/usr/lib/moonmachine-build-tools/bin:${PATH}"
COPY apps/ /build-input/
# Separate build processes from the logged-in user's process-kill shortcuts.
RUN mkdir -p /build /out /usr/lib/moonmachine /tmp/moonmachine-build-home \
    && chown 1001:1001 /build /out /usr/lib/moonmachine /tmp/moonmachine-build-home
USER 1001:1001
RUN bash /build-input/build.sh
FROM ${BASE_IMAGE}
LABEL org.opencontainers.image.title="Moonmachine" \
      org.opencontainers.image.description="Experimental full kernel with K17 FRL/VRR, BORE 6.8.0 and ThinLTO; no AutoFDO" \
      io.cynary.k17.source-commit="8cff674dac5e46b6452d4349ed3f3483d6cff1bc"
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
    libdav1d libshaderc lcms2 xxhash-libs
RUN python3 /tmp/moonmachine-apps/install.py && rm -rf /tmp/moonmachine-apps
COPY tests/test_app_setup.py /tmp/test_app_setup.py
RUN python3 /tmp/test_app_setup.py && rm /tmp/test_app_setup.py
RUN LD_LIBRARY_PATH=/usr/lib/moonmachine/moonlight/usr/lib:/usr/lib/moonmachine/moonlight/usr/lib64 \
    ldd /usr/lib/moonmachine/moonlight/usr/bin/moonlight > /tmp/moonlight-libraries \
    && cat /tmp/moonlight-libraries && ! grep -q 'not found' /tmp/moonlight-libraries \
    && rm /tmp/moonlight-libraries
RUN dnf5 clean all && rm -rf /var/cache/libdnf5 /var/cache/ldconfig/aux-cache /var/lib/dnf/repos && rm -f /var/log/dnf5.log
RUN --mount=type=tmpfs,target=/run --network=none bootc container lint
LABEL org.opencontainers.image.source="https://github.com/Cynary/bazzite-k17" \
      io.cynary.k17.release="moonmachine-20260919.3"
