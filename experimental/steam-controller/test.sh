#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
tmp=$(mktemp -d)
trap 'find "$tmp" -type f -delete; rmdir "$tmp"' EXIT
${CXX:-g++} -std=c++20 -Wall -Wextra -Werror -g -fsanitize=address,undefined test_triton.cpp -o "$tmp/test-triton"
"$tmp/test-triton"
if [[ -n ${SDL_HIDAPI_DIR:-} ]]; then
    ${CXX:-g++} -std=c++20 -Wall -Wextra -Werror -I"$SDL_HIDAPI_DIR" test_sdl_layout.cpp -o "$tmp/test-layout"
    "$tmp/test-layout"
    echo 'PASS: Valve SDL packed layouts match'
fi
