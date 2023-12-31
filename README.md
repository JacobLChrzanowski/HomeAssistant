# HomeAssistant
My HomeAssistant Config
Half the things i thought were true about PyScript turned out to be false, in a good way. I removed a bunch of assumptions i had.

## 1. What is this?
I needed a way to have stateful lights that could be controlled with IKEA Tradri remotes. I implimented that functionality in HomeAssistant in PyScript <https://hacs-pyscript.readthedocs.io/en/latest/>. It leverages zigbee-connected remotes. There is some state kept in individual pyscript session(s?) and also in HomeAssistant 'helper' variables. Why is explained later.

## 2. Why is it a mess?
b.2) No I'm not going to keep configs as homeassistant 'helper' strings. That's convoluted.
b.3) I need to read the PyScript docs more.
c) it's a WIP

## 3. What's the structure to the repo?
If you were to look into homeassistant's file structure it would look about the same. I dump any configs I keep on homeassistant into the config folder. Any strcture from there on out is following homeassistant's.

## 4. What do I need to do the same thing?
- An up to date copy of homeassistant
- PyScript installed on that copy of homeassistant
- All files in the root of config are stubs and contain only relevent config for this repo. Dont overwrite your automations.yaml or configuration.yaml
- Copy files or their contents appropriately, as they exist in the CONFIG folder into homeassistant. The VSCode for HomeAssistant plugin makes copying and working with HA SS folder much easier.

## 5. Why is this all so complicated?
I wanted to build something that could be configured for complex and simple use cases. This used to be simple when it served a single Tradfri E2001 4-button remote. Then I wanted a second remote for a different room, and to also support Tradfri E1810 5-button puck remotes. That necessitated a lot of complexity.
I used to have it where every remote did call its own purpose-built automation, but that was unwieldy. Having a single event handler forward all zha_event events to a pyscript service/event handler is much cleaner. Then the script can filter out what it cares about and what it doesn't ... if that even happens? Will it ever receive events not generated by remotes? IDK! maybe... read on in Implimentation Details: 3

# Implimentation Details
## 1. What the heck is 'All Service Call'?
To let the pyscript event handler be aware of all button presses by any zigbee

## 2. Why do you keep some state in pyscript, and other state in HomeAssistant 'helpers'?
PyScript stores immediate state of lights and 'locales'. I need to keep track of a remote button press to know whether it will be a long press or not, these come in two events. These are short lived events and 'expire' in usefulness moments after they happen. I don't really care about losing that state between script reloads. What is tracked (or will be tracked better) is state of locales. That way if you restart PyScript, any scene change will be correctly applied on top of the current scene.

I store long-term state data in HomeAssistant helpers. For instance if I need to remember what scene is applied to an area a remote controls, that will be stored  as some counter value. Or string. That's up in the air.
Eventually I need to move that to a string value so I don't have a dozen helpers for a dozen remotes, just one helper for one house.
Or I'll need to programmatically create and destroy helpers as needed. That's a 'down the pipe' feature.

For now, when you see 'counter.ikea_r1_counter', understand that as a helper of type Counter:
min value: 0      max value: 4
initial value: 0  step size:1
Entity ID: counter.ikea_r1_counter
Restore last known value on start: yes

## 3. What is this one catch-all automation? Do I need to have my remotes call this automation?
This is as I call it, a catch-all automation. It forwards all zha_event(s) to a pyscript service. You should not have any device directly call this automation, else you'll have pyscript processing each input from that device, twice. You probably don't want that.
This script is designed to have all business logic in the PyScript file. The big reason for shipping all events is so that you don't need to have one automation per remote. That would be silly. It also avoids verbose automation files where each possible action from your remote has its own trigger. I tried that and ended up missing the hold-left and hold-right actions on the Tradfri E1810. This method is cleaner and debug-friendly.

Side note, sometimes zha-events will fire and it won't be because you touched a remote. This began happening when I added the Tradfri E1810 and don't know why. Easy way around this is to action only on events that you recognize.

## 4. Why all the dictionaries? Aren't small lists faster?
Dictionaries are faster in Python. It's a weird language where the two's performance does not cross over even for very small lists. 
