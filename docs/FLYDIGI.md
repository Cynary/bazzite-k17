# Vader 5 Pro integration in development

This branch packages [Flydigi Control](https://github.com/Cynary/flydigi-control),
a controller-friendly configuration app for lighting, Turbo and Fn profile
shortcuts. It uses a pinned source commit from `apps/sources.json`.

The app has passed protocol and offscreen UI tests on the K17. Physical button
mapping in Steam, lighting changes, reconnect behavior and controller-triggered
wake still need hardware validation. This branch must not be promoted as full
Vader support until those checks pass.

The image installation adds `/usr/bin/flydigi-control`, its desktop entry and a
udev rule granting the active desktop user access to the Vader configuration
interface. It does not replace xpad or SDL, create a virtual gamepad, automatically change
Steam controller settings, or enable a wake policy. The app offers an explicit
Native Steam Input permission toggle; this was necessary for native detection
on firmware 7.1.5.0. Restart Steam after enabling it; a receiver reconnect alone did not refresh
the input path in our test.

Use the app's [validation procedure](https://github.com/Cynary/flydigi-control/blob/main/docs/VALIDATION.md)
for the remaining hardware checks. The image build runs its protocol tests and
renders the app offscreen to check runtime dependencies.
