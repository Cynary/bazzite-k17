# Recovery experiments

`frl-recovery-candidate.patch` is the first, rejected experiment. Keeping the
transcoder enabled after a training failure was insufficient: with the source
still in its training phase, the TV-off test produced a FIFO underrun and vblank
and flip timeouts. It is **not** included in `kernel-patches/` or the normal image.

The next experiment additionally ends the source training phase without marking
the sink link trained. It must pass real failure/recovery tests before promotion.
