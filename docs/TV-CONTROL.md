# Turn the TV on with the PC

A console can often wake a TV and select its input over HDMI. This is called CEC.
The K17 doesn't expose a usable CEC controller in the tested Linux setup, so this
part needs another route.

If your TV and receiver can be controlled over the network, Home Assistant can
provide similar behaviour. The exact commands depend on your equipment; there
isn't one configuration that works for every living room.

## Example: Home Assistant

Add your TV and receiver to Home Assistant first. Verify that its controls can:

- Wake the TV and receiver from standby.
- Select the TV input connected to the receiver.
- Select the receiver input connected to the PC.
- Read the currently selected inputs.

Create an automation for PC wake that turns on both devices, waits until the TV
accepts commands, then selects those two inputs. Some TVs need Wake-on-LAN to
wake up: a normal input-selection command may only work once they're awake.
Reserve addresses for the devices in your router so they don't change.

For example, with a PC connected to a receiver's **Game** input and the receiver
connected to the TV's **HDMI 2**, the actions are:

```yaml
# Example Home Assistant actions. Replace the entities and source names.
actions:
  - action: media_player.turn_on
    target:
      entity_id:
        - media_player.living_room_tv
        - media_player.living_room_receiver
  - wait_template: "{{ is_state('media_player.living_room_tv', 'on') }}"
    timeout: "00:00:30"
    continue_on_timeout: false
  - action: media_player.select_source
    target:
      entity_id: media_player.living_room_receiver
    data:
      source: Game
  - action: media_player.select_source
    target:
      entity_id: media_player.living_room_tv
    data:
      source: HDMI 2
```

How you trigger it is up to your setup: a Home Assistant button can wake the PC
and run the actions together, or a service on the PC can call a Home Assistant
webhook after resume. A PC-side trigger must wait for networking to return.
TV startup time can still dominate the delay.

For sleep, **only turn off the TV and receiver if both still select the PC**.
Read both inputs immediately before switching them off. If either device is
unreachable, an input is unknown, or someone has changed inputs, do nothing.
That avoids interrupting someone watching another source.

## Using a USB CEC adapter

An adapter provides a CEC controller that the PC can address over USB. Check the
adapter's video specifications before putting it in the video path: older models
can prevent 4K120, HDR or VRR from passing through. A separate HDMI control
connection may be possible, but routing to the PC's other input depends on the
receiver and needs testing. It isn't a tested plug-and-play option for this image.
