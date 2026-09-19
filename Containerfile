ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-deck@sha256:f956a8f987e40b81990d673a9f5c777691944b45858f4267ea77f2e75c14d27b
FROM ${BASE_IMAGE} AS base
FROM docker.io/library/fedora@sha256:43b29f65a41eb9c35e1cd5323e3bdf3b655c2357a9f4f1ff2f9c2798e5045d80 AS builder
RUN dnf install -y gcc make binutils elfutils-libelf-devel openssl-devel dwarves python3 kmod cpio zstd xz bc bison flex diffutils findutils curl tar gzip git-core && dnf clean all
ARG KERNEL_RELEASE=7.2.4-ogc3.1.fc44.x86_64
ARG SOURCE_BASE_COMMIT=43d13ad09df8a544c032f75dc84fddd2aefe8f76
ARG SOURCE_COMMIT=f37b49ee569bbf42bb8d1a675040f28c8b26cac6
COPY --from=base /usr/src/kernels/${KERNEL_RELEASE}/ /work/kernel/
COPY --from=base /usr/lib/modules/${KERNEL_RELEASE}/vmlinuz /work/stock-vmlinuz
COPY scripts/build-modules.sh /work/build-modules.sh
COPY kernel-patches/ /work/patches/
RUN /work/build-modules.sh
FROM base AS final
ARG BASE_IMAGE
ARG SOURCE_COMMIT=f37b49ee569bbf42bb8d1a675040f28c8b26cac6
ARG KERNEL_RELEASE=7.2.4-ogc3.1.fc44.x86_64
LABEL org.opencontainers.image.title="Bazzite K17 FRL/VRR candidate" \
      org.opencontainers.image.source="https://github.com/Cynary/bazzite-k17" \
      org.opencontainers.image.description="Stock Bazzite kernel with matched experimental Xe/display-helper replacements" \
      org.opencontainers.image.base.name="${BASE_IMAGE}" \
      io.cynary.k17.source-commit="${SOURCE_COMMIT}"
COPY --from=builder /out/ /usr/share/k17-frl/build/
COPY scripts/install-modules.sh /tmp/k17-install-modules.sh
RUN /tmp/k17-install-modules.sh && rm /tmp/k17-install-modules.sh
RUN --mount=type=tmpfs,target=/run --network=none bootc container lint
