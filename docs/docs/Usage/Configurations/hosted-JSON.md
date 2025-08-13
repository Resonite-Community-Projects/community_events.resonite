# Hosted JSON

!!! danger "Not recommended"

    This method is not recommended and will be only accepted in the case you can't use Discord but this is not garanted.
    Keep in mind the process is the same than explained for the [Discord Integration](discord.md) in the end.

It's possible to expose your events with a JSON file exposed somewhere.

The content of your JSON file should be an array of event objects, each conforming to the following schema:

### JSON Schema Definition

| Field | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `event_id` | `string` | Yes | A unique identifier for your event. This should be unique across all your events. | `CHILLING01` |
| `name` | `string` | Yes | The title of your event. | `Chilling Session` |
| `start_time` | `string` | Yes | The start date and time of your event in [ISO 8601 format](https://en.wikipedia.org/wiki/ISO_8601). Must include timezone information. | `2025-06-14T00:00:00+00:00` |
| `end_time` | `string` | Yes | The end date and time of your event in [ISO 8601 format](https://en.wikipedia.org/wiki/ISO_8601). Must include timezone information. | `2025-06-14T02:00:00+00:00` |
| `location` | `string` | Yes | A string describing the location of your event (e.g., "The Chill Zone World"). | `The chill session` |
| `session_url` | `string` | Yes | The Resonite session URL for the event. | `resonite:///S-U-1REbXt5AflQ:Chill` |
| `description` | `string` | Yes | A detailed description of your event. | `Let's come chill together!` |


### Validation and Error Handling

Our system will periodically fetch your JSON file. If the file is unavailable or does not conform to the required schema, your events will not be updated.

### Refresh Rate

Please note that we fetch hosted JSON files approximately every 15 minutes. It may take some time for your changes to appear in the event listings after you update your JSON file.

## Example

```json
[
  {
    "event_id": "CHILLING01",
    "name": "Chilling",
    "start_time": "2025-06-14T00:00:00+00:00",
    "end_time": "2025-06-14T02:00:00+00:00",
    "location": "The chill session",
    "session_url": "resonite:///S-U-1REbXt5AflQ:Chill",
    "description": "Let's come chill together!"
  },
  {
    "event_id": "WEEKLY_MEETUP_001",
    "name": "Weekly Community Meetup",
    "start_time": "2025-06-15T18:00:00-07:00",
    "end_time": "2025-06-15T19:30:00-07:00",
    "location": "Community Hub World",
    "description": "Our regular community gathering. Come discuss new features, share creations, and hang out!"
  }
]
```