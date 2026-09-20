# Turn the TV on and off with the PC

A couch PC should wake the TV, select the right input, and leave it alone when
someone is watching something else. HDMI calls this CEC. The K17 doesn't expose
a usable CEC controller in the tested Linux setup, but network commands can
provide similar behaviour.

This guide uses an example wiring arrangement:

```text
Moonmachine → Denon AUX2 → LG TV HDMI 2
```

Choose either **Home Assistant** or **direct LG/Denon control**, then install the
PC hooks below. Both options wake the equipment on startup/resume and request
standby on sleep/shutdown. The shutdown hook also runs during a reboot.

All addresses, MAC addresses, entity names and webhook IDs below are examples.
Replace them before enabling anything. Reserve device addresses in your router.
These examples are optional; installing Moonmachine does not enable them.

## Option 1: Home Assistant

Add the TV and receiver to Home Assistant and verify their power and input
controls first. In Developer Tools → States, check the actual `source` values:
Home Assistant's friendly name `HDMI 2` is different from LG's direct command
value `HDMI_2`. Receiver source names can also be renamed.

For an LG TV, enable its network wake option (often **Turn on via Wi-Fi** or
**Mobile TV On**) and Quick Start+ if available. Add the Wake on LAN integration
by adding `wake_on_lan:` to Home Assistant's `configuration.yaml` and restarting
Home Assistant. Use the MAC of the TV's connected network interface.

Create an automation, open **Edit in YAML**, and use this example. Generate two
unpredictable webhook IDs (for example, with `openssl rand -hex 24`) and replace
the placeholders here and in the PC configuration. Keep webhooks local-only.

```yaml
alias: Moonmachine TV and receiver
mode: restart
triggers:
  - trigger: webhook
    webhook_id: REPLACE_WITH_RANDOM_WAKE_ID
    allowed_methods: [POST]
    local_only: true
    id: wake
  - trigger: webhook
    webhook_id: REPLACE_WITH_RANDOM_STANDBY_ID
    allowed_methods: [POST]
    local_only: true
    id: standby
actions:
  - choose:
      - conditions: "{{ trigger.id == 'wake' }}"
        sequence:
          - parallel:
              - sequence:
                  - action: media_player.turn_on
                    target:
                      entity_id: media_player.living_room_receiver
                  - wait_template: "{{ is_state('media_player.living_room_receiver', 'on') }}"
                    timeout: "00:00:30"
                    continue_on_timeout: false
                  - action: media_player.select_source
                    target:
                      entity_id: media_player.living_room_receiver
                    data:
                      source: AUX2
              - sequence:
                  - action: wake_on_lan.send_magic_packet
                    data:
                      mac: "02:00:00:00:00:20"
                      broadcast_address: "192.0.2.255"
                  - wait_template: "{{ is_state('media_player.living_room_tv', 'on') }}"
                    timeout: "00:00:30"
                    continue_on_timeout: false
                  - action: media_player.select_source
                    target:
                      entity_id: media_player.living_room_tv
                    data:
                      source: HDMI 2
      - conditions: "{{ trigger.id == 'standby' }}"
        sequence:
          - action: homeassistant.update_entity
            target:
              entity_id:
                - media_player.living_room_tv
                - media_player.living_room_receiver
          - condition: template
            value_template: >-
              {{ is_state('media_player.living_room_tv', 'on')
                 and is_state('media_player.living_room_receiver', 'on')
                 and state_attr('media_player.living_room_tv', 'source') == 'HDMI 2'
                 and state_attr('media_player.living_room_receiver', 'source') == 'AUX2' }}
          - action: media_player.turn_off
            target:
              entity_id:
                - media_player.living_room_tv
                - media_player.living_room_receiver
```

`mode: restart` cancels a pending wake sequence when standby arrives, or a pending
standby sequence when wake arrives. An unknown/unavailable device or a different
input fails the standby condition. There is no delayed standby retry.
Home Assistant's input state can still lag the physical device, even after an
update request. The direct example below reads both devices immediately before
standby and is preferable when that check matters most.

On the PC, create `/etc/moonmachine/av-webhooks.conf`:

```sh
WAKE_URL='http://homeassistant.example.test:8123/api/webhook/REPLACE_WITH_RANDOM_WAKE_ID'
STANDBY_URL='http://homeassistant.example.test:8123/api/webhook/REPLACE_WITH_RANDOM_STANDBY_ID'
```

Create the directory with `sudo install -d /etc/moonmachine`, edit the file with
`sudoedit`, then protect it with `sudo chmod 600 /etc/moonmachine/av-webhooks.conf`.
Create `/usr/local/sbin/moonmachine-av` with this content:

```bash
#!/bin/bash
set -eu
source /etc/moonmachine/av-webhooks.conf
case "${1:-}" in
  wake)
    # NetworkManager may still be reconnecting after resume.
    for attempt in {1..15}; do
      if curl --fail --silent --show-error --connect-timeout 1 --max-time 2 \
          -X POST "$WAKE_URL"; then
        exit 0
      fi
      sleep 1
    done
    exit 1
    ;;
  standby)
    # Don't queue an off request to arrive after someone switches sources.
    exec curl --fail --silent --show-error --connect-timeout 1 --max-time 4 \
      -X POST "$STANDBY_URL"
    ;;
  *) echo 'Usage: moonmachine-av wake|standby' >&2; exit 2 ;;
esac
```

Run `sudo chmod 755 /usr/local/sbin/moonmachine-av`. A successful webhook response
means Home Assistant accepted the request; its automation trace shows whether the
equipment actually responded. Test both commands manually before adding hooks.

References: [webhooks](https://www.home-assistant.io/docs/automation/trigger/#webhook-trigger),
[LG webOS](https://www.home-assistant.io/integrations/webostv/),
[Wake on LAN](https://www.home-assistant.io/integrations/wake_on_lan/).

## Option 2: Send commands directly to an LG TV and Denon AVR

This avoids waiting for Home Assistant to notice that the TV is online. The
[example scripts](../examples/tv-control/) use LG's paired webOS connection and
Denon's local HTTP interface, as supported by models such as the LG G1 and
Denon AVR-S760H. Other models and firmware may need different endpoints.
The examples were checked with aiohttp 3.14.3 and aiowebostv 0.10.0.

The wake script contacts the receiver, sends TV wake packets, and tries LG's
`tv/switchInput` command as soon as the TV accepts a connection. It doesn't wait
for a Home Assistant state update before selecting HDMI 2. This approach reduced
input-selection latency in testing, but can't eliminate Ethernet link startup
or the TV's own standby recovery time. An input command alone is not a reliable
way to wake a sleeping TV.

The standby script checks the TV and receiver twice, then sends standby only if
both are active and still select the configured inputs. An unreachable device,
missing pairing key, or unknown input means **do nothing**. The checks have a
three-second deadline. They aren't an atomic transaction: someone can still
change input in the small interval between the final check and the commands.

### Install and pair

Run these commands from a checkout of this repository. They install only the
example scripts, not any credentials. Python 3.11 or newer is required.

```sh
sudo install -d -m 700 /var/lib/moonmachine-av
sudo install -d /etc/moonmachine
sudo install -m 644 examples/tv-control/direct_av.py examples/tv-control/sleep_av.py /var/lib/moonmachine-av/
sudo install -m 600 examples/tv-control/av.example.json /etc/moonmachine/av.json
sudo python3 -m venv /var/lib/moonmachine-av/venv
sudo /var/lib/moonmachine-av/venv/bin/pip install 'aiohttp>=3.11,<4' 'aiowebostv>=0.4,<1'
sudoedit /etc/moonmachine/av.json
```

Set the TV's address and Wi-Fi/Ethernet MAC, receiver URL, and your subnet's
broadcast address. The example selects `HDMI_2` / `com.webos.app.hdmi2` on LG and
`AUX2` on Denon. Use the receiver's protocol input code, not a renamed display
label. Denon's network control must remain enabled in standby.

With the TV already on, run:

```sh
sudo /var/lib/moonmachine-av/venv/bin/python /var/lib/moonmachine-av/direct_av.py pair
```

Accept the connection prompt with the TV remote. The pairing key is saved locally
in `/var/lib/moonmachine-av/tv-key.json`, readable only by root. This example uses
the TV's self-signed HTTPS/WebSocket endpoint without certificate verification;
keep it on a trusted LAN. Denon's example endpoint is unencrypted HTTP.

Check connectivity and inputs without powering anything off:

```sh
sudo /var/lib/moonmachine-av/venv/bin/python /var/lib/moonmachine-av/direct_av.py status
sudo /var/lib/moonmachine-av/venv/bin/python /var/lib/moonmachine-av/sleep_av.py --check
```

Create `/usr/local/sbin/moonmachine-av` with the following content, then run
`sudo chmod 755 /usr/local/sbin/moonmachine-av`:

```sh
#!/bin/sh
case "${1:-}" in
  wake) exec /var/lib/moonmachine-av/venv/bin/python -u /var/lib/moonmachine-av/direct_av.py wake ;;
  standby) exec /var/lib/moonmachine-av/venv/bin/python -u /var/lib/moonmachine-av/sleep_av.py ;;
  *) echo 'Usage: moonmachine-av wake|standby' >&2; exit 2 ;;
esac
```

Test `sudo moonmachine-av wake`, then `sudo moonmachine-av standby` while both
inputs point to the PC. Also test standby with another TV/receiver input selected:
it should leave both devices alone.

### If the sleeping TV ignores broadcast wake packets

Some Wi-Fi setups deliver unicast wake packets more reliably. Set `unicast_wake`
to `true` only if the PC and TV are on the same subnet. The script then installs a
permanent IP-to-MAC neighbour entry before sending each wake packet, so the PC
doesn't wait for a sleeping TV to answer ARP. Use a reserved IP and the correct
MAC; an incorrect entry prevents communication. Routed destinations are rejected.

To undo that neighbour entry, run `sudo ip neigh del TV_ADDRESS dev INTERFACE`,
using the TV address and interface reported by `ip route get TV_ADDRESS`.
The normal broadcast mode doesn't modify neighbour entries.

## Connect either option to startup, resume, sleep and shutdown

Install just one of the `/usr/local/sbin/moonmachine-av` wrappers above. The units
below call that wrapper, so the lifecycle behaviour is the same for either option.
Do not enable both this setup and a second TV-control hook for the same PC.

Create `/etc/systemd/system/moonmachine-av-wake.service`:

```ini
[Unit]
Description=Wake TV and receiver and select the PC
After=NetworkManager.service network.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/moonmachine-av wake
TimeoutStartSec=100
```

Create `/etc/systemd/system/moonmachine-av-session.service`:

```ini
[Unit]
Description=TV control on PC startup and shutdown
Wants=network.target
After=NetworkManager.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/true
ExecStartPost=/usr/bin/systemctl --no-block start moonmachine-av-wake.service
ExecStop=/usr/bin/systemctl stop moonmachine-av-wake.service
ExecStop=/usr/local/sbin/moonmachine-av standby
TimeoutStopSec=6

[Install]
WantedBy=multi-user.target
```

The session unit stays active after startup. On orderly shutdown or reboot it
stops any wake attempt and checks inputs before sending standby. Its ordering
keeps NetworkManager available until the stop commands finish. Power loss or a
forced power-off cannot run this hook.

Create `/etc/systemd/system/moonmachine-av-sleep.service`:

```ini
[Unit]
Description=TV control around PC sleep
DefaultDependencies=no
Before=sleep.target
Conflicts=moonmachine-av-wake.service
After=moonmachine-av-wake.service
StopWhenUnneeded=yes

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=-/usr/local/sbin/moonmachine-av standby
ExecStop=/usr/bin/systemctl --no-block start moonmachine-av-wake.service
TimeoutStartSec=6
TimeoutStopSec=6

[Install]
WantedBy=sleep.target
```

This sends conditional standby **before** suspend/hibernate and starts wake
control **after** resume. Wake retries handle the network returning. Standby is
bounded and a command failure doesn't prevent the PC sleeping. Use these units
rather than a late shutdown script: networking may already be gone by then.

Enable the hooks once the manual tests work:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now moonmachine-av-session.service
sudo systemctl enable moonmachine-av-sleep.service
```

The first command that starts the session service also wakes the TV/receiver.
Inspect timings with:

```sh
journalctl -b -u moonmachine-av-wake -u moonmachine-av-session -u moonmachine-av-sleep
```

Test a normal boot, suspend/resume, and shutdown. Repeat with another input
selected before sleep: neither device should enter standby. For Home Assistant,
also inspect the automation trace; for direct control, the logs include elapsed
times and the input readings. These public examples have syntax and standby-guard
tests; verify lifecycle behaviour with your own equipment before relying on it.

To disable automatic control without turning the TV off as a side effect, disable
the hooks and replace the wrapper with a no-op before stopping the active session:

```sh
sudo systemctl disable moonmachine-av-session.service moonmachine-av-sleep.service
sudo systemctl stop moonmachine-av-wake.service
sudo mv /usr/local/sbin/moonmachine-av /usr/local/sbin/moonmachine-av.disabled
printf '#!/bin/sh\nexit 0\n' | sudo tee /usr/local/sbin/moonmachine-av >/dev/null
sudo chmod 755 /usr/local/sbin/moonmachine-av
sudo systemctl stop moonmachine-av-session.service
```

The files under `/etc`, `/usr/local` and `/var/lib` persist across image updates.
If an update changes Python's minor version, recreate the direct-control virtual
environment and reinstall its dependencies; retain the configuration and TV key.

To run the standby checks without contacting any equipment, use a Python
environment containing the two dependencies above, then run from the repository:

```sh
MOONMACHINE_AV_CONFIG="$PWD/examples/tv-control/av.example.json" \
  python3 -m unittest discover -s examples/tv-control -p 'test_*.py'
```

## Using a USB CEC adapter instead

Check an adapter's video specifications before placing it in the video path:
older models can prevent 4K120, HDR or VRR from passing through. A separate HDMI
control connection may be possible, but routing to the PC's other input depends
on the receiver and needs testing. It isn't a tested plug-and-play option for
this image.
