# Component sources

Moonmachine builds tested commits from these repositories. The image repository
owns packaging and defaults; component changes belong in their own forks.

| Component | Repository | Branch |
| --- | --- | --- |
| Image | [bazzite-k17](https://github.com/Cynary/bazzite-k17) | main |
| Kernel and Intel display driver | [linux-k17-frl](https://github.com/Cynary/linux-k17-frl) | k17-bore-thinlto |
| Xbox wireless driver | [xonedo](https://github.com/Cynary/xonedo) | moonmachine |
| Moonlight | [moonlight-qt](https://github.com/Cynary/moonlight-qt) | moonmachine |
| Gamescope | [gamescope](https://github.com/Cynary/gamescope) | moonmachine |
| libplacebo | [libplacebo](https://github.com/Cynary/libplacebo) | moonmachine |
| Streaming protocol | [moonlight-common-c](https://github.com/Cynary/moonlight-common-c) | master |
| Windows host | [Vibepollo](https://github.com/Cynary/Vibepollo) | master |
| Windows virtual controllers | [libvirtualgamepad](https://github.com/Cynary/libvirtualgamepad) | main |
| Buddy | [moondeck-buddy](https://github.com/Cynary/moondeck-buddy) | main |

The first migration into the application and xonedo branches preserved the exact
source trees produced by the former build patches. Full application revisions
are in `apps/sources.json`; kernel and xonedo revisions are in the kernel build
notes. A branch moving does not change a published image: each build pins full
commit IDs. The streaming protocol and Windows forks are development sources;
creating them does not enable native controller forwarding in a released image.
