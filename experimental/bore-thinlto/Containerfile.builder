FROM localhost/k17-module-builder:44
RUN dnf -y install clang lld llvm rust rust-src bindgen-cli clang-libs cpio rsync perl openssl && dnf clean all
