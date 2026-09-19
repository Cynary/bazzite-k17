# Association retry diagnosis (2026-09-18)

A demonstrated defect, distinct from the still-unresolved USB overflow and
command-stall observations. No claim that all restart failures are fixed.

Current OGC xonedo 982cbcb silently returns from add_client when the source MAC
already has a client slot. That avoids allocating duplicate WCIDs, but it also
suppresses association responses when a controller retries the request. Having
a WCID is not evidence that association or GIP initialization completed.

In a natural failed restart, USB traffic showed repeated association requests
from the actual paired controller, one initial response, one occupied WCID,
and no Xbox input device. An extra probe-time USB reset did not prevent this.

Controlled fault injection withheld the first response after programming the
WCID. With existing duplicate handling, retries were ignored and no input
device appeared. Enabling retry replies at runtime caused the next request
to receive a response at 22:20:11; the real Xbox input device registered at
22:20:12. The user confirmed that the controller connected and navigated Steam.
No reset, replug, re-pair, or firmware change occurred during this transition.

The experimental patch reuses the existing WCID and sends another association
response, without allocating another client or issuing another firmware
ADD_CLIENT command. It has also passed two normal connected-controller
restarts with the shutdown-poweroff and extra-USB-reset workarounds disabled;
both traces showed an association retry being answered.

These hardware tests used a diagnostic build with the same response logic,
not a release build of the standalone patch. Fault injection was disabled for
the restart tests. The clean patch still needs its own build/deployment checks.

Raw USB captures stay local because received radio frames can contain unrelated
wireless-network data. No upstream submission has been made.

Packet counts: natural stuck-handshake capture had 56 controller association
requests and one host response. Controlled fault-injection capture had 39
requests and one response, sent only after enabling retry handling. First
normal reboot with retry fix had three requests and two responses. Counts
exclude unrelated wireless frames and are derived from decoded USB records.

The standalone patch built successfully against 7.2.4-ogc3.1.fc44.x86_64;
xone_dongle srcversion D6FE09A44192045F57D7A85, xone_gip matches stock
202AABE021C636443A21D63. Clean-module hardware validation remains pending.
