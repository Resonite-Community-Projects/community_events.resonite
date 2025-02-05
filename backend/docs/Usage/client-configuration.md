# Client Configuration

!!! construction "This need to be documented"

!!! note

    Probably for the future new resonite community web client made by Phil


# Legacy WebUI client

The WebUI client is directly using the functions internally and don't talk to the API in HTTP. Its use a simple css
framework called [Bulma](https://bulma.io/) and are loaded directly from differents CDN for now.

Date are formated directly without taking in account of the timezone of the webbrowser.

There is a support of the discord timestamp but only for the `R` format.

And the resonite session URL is automaticaly detected from the description if no URL already present in the locatization parameter.
It will automaticaly use the first, and only the first, URL starting with `http(s)://cloudx.azurewebsites.net` for set the locatization
parameter.

![WebUI client](https://github.com/Resonite-Community-Projects/community_events.resonite/assets/76159594/0a78fc1e-9250-41ee-a162-004076f13cb8)

