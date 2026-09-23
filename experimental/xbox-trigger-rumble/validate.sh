#!/bin/bash
set -euo pipefail
root=${XBOX_TRIGGER_ROOT:-$HOME/xbox-trigger-rumble-20260923}
marker=/usr/share/moonmachine/xbox-trigger-candidate.json
case ${1:-} in
 --restore)
    sudo bootc switch --enforce-container-sigpolicy ghcr.io/cynary/bazzite-k17:moonmachine
    echo 'Published channel staged. Reboot when ready.'; exit;;
 --stage)
    test -s "$root/oci-final/index.json"
    expected=$(cat "$root/candidate-digest")
    actual=$(skopeo inspect --raw "oci:$root/oci-final" | sha256sum | cut -d' ' -f1)
    test "sha256:$actual" = "$expected"
    if pgrep -x moonlight >/dev/null; then echo 'Close the Moonlight stream first.' >&2; exit 1; fi
    echo 'This stages a LOCAL experimental kernel + xone + SDL image. Nothing is published.'
    echo 'The normal image remains available as rollback. Save other work before rebooting.'
    read -r -p 'Type stage to proceed: ' reply; test "$reply" = stage
    sudo bootc switch --transport oci "$root/oci-final"
    echo 'Candidate staged. Run sudo systemctl reboot, reconnect, then rerun this script without --stage.';exit;;
 --list|'') ;;
 *) echo "Usage: $0 [--stage|--list|--restore]";exit 2;;
esac
if ! test -f "$marker"; then
    echo 'The candidate is not booted. Run this script with --stage, then reboot.';exit 1
fi
export LD_LIBRARY_PATH=/usr/lib/moonmachine/moonlight/usr/lib
if [[ ${1:-} == --list ]]; then exec /usr/libexec/xbox-motor-test --list; fi
/usr/libexec/xbox-motor-test --list
read -r -p 'Enter the Xbox controller index shown above: ' index
[[ $index =~ ^[0-9]+$ ]] || exit 2
exec /usr/libexec/xbox-motor-test --run "$index"
