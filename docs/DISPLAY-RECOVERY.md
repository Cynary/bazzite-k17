# Returning to the picture after sleep

Two separate fixes help Gaming Mode recover when the PC or receiver wakes.

## HDMI link recovery

A receiver can keep reporting that it is connected while losing its HDMI FRL
configuration. The PC may still report 4K120 HDR even though no picture reaches
the TV. Training can also fail if the receiver is still starting up.

The display driver checks active FRL links every two seconds. It reads the
receiver's configuration, readiness and lane-lock status. If the link is lost,
it requests a full modeset through the driver's normal commit path. A healthy
link is checked without resetting it. Checks stop when the output is disabled.
Training timeouts no longer lower the cached maximum link rate; explicit rate
change requests from the receiver still can.

The failure path also keeps the FRL timing engine enabled so recovery commits
can complete. This addresses a possible early-training failure path identified
in the code; that particular path has not been isolated with fault injection.

On the K17, the patch recovered through five receiver standby/on cycles and
two subsequent sleep/resume cycles. One receiver cycle and the final resume
included real training timeouts followed by automatic recovery. Those tests
had no new display underruns or flip/commit timeouts, and the final picture was
confirmed visually. They validate that setup, not every receiver or cable.
The overhead of periodic healthy-link checks has not been benchmarked.

The source patch is [0053](../kernel-patches/0053-drm-intel-hdmi-recover-lost-frl-sink-state.patch).
The corrected `frl4` module is included in `moonmachine-20260922.2`; its installed
checksum and recovery marker were verified. Assembled-image recovery checks
are recorded in [streaming validation](STREAMING-VALIDATION.md).

## Steam's blocked-sleep overlay

Steam can start its sleep animation before asking the system to suspend. If a
build or another application blocks sleep, Steam may leave that animation over
the library. Once the video ends, it looks like a black screen even though the
HDMI connection is working.

The `steam-inhibitor-guard` user service mirrors the system's sleep inhibitors
into Steam's own suspend blocker. This prevents the animation from starting
while sleep is blocked. It releases only its own blocker, and a fifteen-second
lease expires if the guard stops responding.

This is a compatibility mitigation using Steam's internal `BlockSuspendAction`
API, not a change to Steam itself. It requires the local CEF debugging endpoint
that Moonmachine enables for Decky. If Steam changes that API, the service logs
the failure rather than replacing Steam's files. Check compatibility after
Steam updates. The service uses Python GI, Gio and Soup 3.

Validation covered a real blocked-sleep request, release of the blocker when
the inhibitor ended, preservation of another Steam blocker, and normal sleep
and resume. The guard does not control a TV or receiver.

```sh
journalctl --user -u steam-inhibitor-guard.service
journalctl -b -k | grep -Ei 'FRL|training|underrun|flip.*timeout'
```

An active DRM mode alone does not prove a picture is visible. Receiver link
status covers the GPU-to-receiver connection; TV power/input state and Steam's
UI are separate checks.
