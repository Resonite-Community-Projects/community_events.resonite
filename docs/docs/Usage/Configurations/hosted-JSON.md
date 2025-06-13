# Hosted JSON

!!! danger "Not recommended"

    This section is recommend for peoples who know what they are doing. If you don't know what
    you are doing please refer to [[discord]].

    The information here is pretty light for this reason.

It's possible to expose your even with a JSON file exposed somewhere. The only thing you have to do
is to send me the URL to this JSON file.

The content should be the following:

```
[
  {
    // A unique ID for your event
    "event_id": "CHILLING01",
    // The name of your event
    "name": "Chilling",
    // The start date of your event
    "start_time": "2025-06-14T00:00:00+00:00"
    // The end date of your event
    "end_time": "2025-06-14T02:00:00+00:00",
    // The location of your event
    "location": "The chill session",
    // The Resonite url of the session
    "session_url": "S-U-1REbXt5AflQ:Chill",
    // The description of your event
    "description": "Let's come chill together!",
  },
  {...}
]
```