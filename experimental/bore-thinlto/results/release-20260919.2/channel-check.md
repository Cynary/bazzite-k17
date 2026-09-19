# Moonmachine channel validation — 2026-09-19

- Published exact tested OCI digest: `sha256:01921691cf33b54dd97b9ea3f9239a591a74a595b79efebd8e4e2320d65f4916`.
- [Publisher](https://github.com/Cynary/bazzite-k17/actions/runs/35475491632): success.
- [Promotion](https://github.com/Cynary/bazzite-k17/actions/runs/35475773161): success.
- K17 independently verified the public image with Cosign and a fresh Skopeo copy using `/etc/containers/policy.json` (repository-specific `sigstoreSigned`, `matchRepository`). The earlier wrong-key check rejected the preceding release cryptographically.
- K17 booted with origin `ghcr.io/cynary/bazzite-k17:moonmachine`, transport `registry`, signature `containerPolicy`, version `44.20260919`, and the same digest above.
- Startup: 29.045 seconds; boot verifier passed; zero failed services. Recovery timer disarmed and working deployment pinned.
- `bootc upgrade --check`: no changes in signed Moonmachine origin.
- `uupd update-check --json`: `update_available: false`, exit 77 (the expected current-image result).
- The local OCI hardware boot also passed MoonDeck launch/exit testing with Overcooked! 2. Host process and stream stopped after local Steam exit. MoonDeck 1.12.2-cynary.1 and Decky's freeze remained intact.
- Initial FRL training failed once on each checked boot and recovered to 4K120/30 bpp. No observed Oops, GPU hang, underrun or flip timeout. Existing firmware ACPI warnings remain. These remote checks do not substitute for TV-side visual qualification or prove future upgrades regression-free.
