#!/bin/bash
set -euo pipefail
cd /work
# Archive builds have no Git-derived suffix; make the ABI suffix explicit.
/work/bore-source/scripts/config --file /work/bore-build/.config --set-str LOCALVERSION '-k17bore1+'
make -C /work/bore-source O=/work/bore-build LLVM=1 olddefconfig rustavailable
for setting in SCHED_BORE LTO_CLANG_THIN DEBUG_INFO_BTF; do
 grep -qx "CONFIG_${setting}=y" /work/bore-build/.config
done
! grep -Eq '^CONFIG_(AUTOFDO_CLANG|PROPELLER_CLANG)=y$' /work/bore-build/.config
{ clang --version; ld.lld --version; rustc --version; bindgen --version; } > /work/bore-build/toolchain.txt
make -C /work/bore-source O=/work/bore-build LLVM=1 LD='ld.lld --threads=2' -j8 bzImage modules
