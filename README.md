# HomeAssistant
My HomeAssistant Config

## 1. What is this?
I needed a way to have stateful lights that could be controlled with IKEA Tradri remotes. I implimented that functionality in HomeAssistant in PyScript <https://hacs-pyscript.readthedocs.io/en/latest/>. It leverages zigbee-connected remotes. There is some state kept in individual pyscript session(s?) and also in HomeAssistant 'helper' variables. Why is explained later.

## 2. Why is it a mess?
PyScript has some functionality missing and namely,
a) cannot import modules local to your directory, your script must be entirely contianed in one file
b) can use yaml as configs I don't want to wade through yaml's just yet.
b.2) No I'm not going to keep configs as homeassistant 'helper' strings. That's convoluted.
b.3) I need to read the PyScript docs more.
c) it's a WIP

## 3. What's the structure to the repo?
If you were to look into homeassistant's file structure it would look about the same. I dump any configs I keep on homeassistant into the config folder. Any strcture from there on out is following homeassistant's.

## 4. What do I need to do the same thing?
- An up to date copy of homeassistant
- PyScript installed on that copy of homeassistant
- Copy files or their contents as they exist in the CONFIG folder into homeassistant. The VSCode for HomeAssistant plugin makes that much easier
- I think I copied all the configs I needed but if something's missing, let me know w/ an issue.
- Don't overwrite your automations.yaml, I only have things relevant to my functionality in this repo.

## 5. Why is this all so complicated?
I wanted to build something that could be configured for complex and simple use cases. This used to be simple when it served a single Tradfri E2001 4-button remote. Then I wanted a second remote for a different room, and to also support Tradfri E1810 5-button puck remotes. That necessitated some change to prevent an explosion in duplicitous and verbose automations.
I used to have it where every remote did call its own purpose-built automation, but that was unwieldy. Having a single event handler handle all zha_event events and ship them to a pyscript event handler is much cleaner. Then the script can filter out what it cares about and what it doesn't ... if that even happens? Will it ever receive events not generated by remotes? IDK! maybe... read on in Implimentation Details: 3

# Implimentation Details
## 1. What the heck is 'All Service Call'?
To let the pyscript event handler be aware of all button presses by any zigbee

## 2. Why do you keep some state in pyscript, and other state in HomeAssistant 'helpers'?
Pyscript stores immediate state, for instance, if I need to keep track of a remote button press, and I need to know whether it was pressed while an event handler is running, I don't really care about losing state between script reloads. In real usage and not when developing, I don't think pyscript will reload that very often. And is very unliekly to while I am pressing a button. It's a non-concern edge case.

I store long-term state data in HomeAssistant helpers. For instance if I need to remember what scene is applied to an area a remote controls, that will be stored  as some counter value.
Eventually I need to move that to a string value so I don't have a dozen helpers for a dozen remotes, just one helper for one house.
Or I'll need to programmatically create and destroy helpers as needed. That's a 'down the pipe' feature.

For now, when you see 'counter.ikea_r1_counter', understand that as a Counter type helper:
min value: 0      max value: 4
initial value: 0  step size:1
Entity ID: counter.ikea_r1_counter
Restore last known value on start: yes

## 3. What is this one catch-all automation? Do I need to have my remotes call this automation?
This is as it is called, a catch-all automation. It catches all zha_event(s) and ships them to a pyscript service. You should not have a remote call this automation, else you'll have pyscript processing each input from that remote twice. You probably don't want that.
This script is designed to have all business logic in the pyscript file. The big reason for shipping all events is so that you don't need to have one automation per remote (that would be silly), and to avoid verbose automation files where each possible action from your remote has its own trigger. I tried that and ended up missing the hold-left and hold-right actions on the Tradfri E1810.

## 4. Why all the lists? Aren't dictionaries faster?
Ah yeah. I don't think so? At least not for the small lists dealt with in this script.
Dictionaries may be O(1) and lists O(n) to retrieve items, but it can take much longer to compute a hash than to loop through a list until an item is found. I understand Python is not a speed king, nor is it exactly slow, but I want to keep the overhead as low as I can for the embedded systems HomeAssistant runs on. Plus, one button press dereferences quite a bit of data due to how extensible I tried to make this, so I would rather loop through 5 lists, than compute 5 hashes. I haven't run microbenchmarks for this but I have a feeling that dictionaries would only become faster than lists once the lists grew to be more than a few hundred, perhaps a thousand entries long.
And that's just not going to happen here.
