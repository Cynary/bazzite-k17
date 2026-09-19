# Recovery experiments

`frl-recovery-candidate.patch` is the first, rejected experiment. Keeping the
transcoder enabled after a training failure was insufficient: with the source
still in its training phase, the TV-off test produced a FIFO underrun and vblank
and flip timeouts. It is **not** included in `kernel-patches/` or the normal image.

The next experiment additionally ends the source training phase without marking
the sink link trained. It must pass real failure/recovery tests before promotion.

Candidate 2 passed its first real TV-off recovery test on 2026-09-18:
- Stock kernel 7.2.4-ogc3.1.fc44.x86_64, replacement Xe SHA256
  e675b0715bdb2a04dc742f911a280575f785eaaf16468755ef065646df6dd39e.
- Restarted Gaming Mode with the TV/AVR asleep; FRL training failed at
  17:35:02 PDT as expected. Hardware vblank continued.
- After waking the AVR/TV, FRL retrained at rate=40 at 17:35:34. Input
  switching caused two further transient failures, followed by successful
  retraining at 17:35:40 and 17:35:53. No session restart or reboot was needed.
- No FIFO underrun, vblank timeout, flip timeout, state mismatch, WARNING
  or BUG was found in the captured failure/recovery interval.
- Debugfs returned to 3840x2160@120, RGB 30 bpp, no dithering, four
  10-Gbps lanes. Hardware vblank intervals varied after recovery.

This is software evidence from one recovery cycle, not visual confirmation
of picture quality or comprehensive cold-boot/resume validation. Candidate 2 was subsequently visually validated through a normal Steam launch
and is now included as patch 0052. Broad cold-boot/resume validation remains
incomplete; see PERFORMANCE.md for release qualification limits.

The first private CI image built and pushed successfully, with package
visibility verified private, but signing failed because Cosign defaults to
a TUF signing config incompatible with --tlog-upload=false. Explicitly
disable that config when using our private signing key and no public log.
