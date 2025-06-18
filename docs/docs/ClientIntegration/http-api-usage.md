# HTTP API usage

This API is available in two different versions.

The V1 is the legacy API but is still the one that you need to use if developing a client and it return only the
events.

The V2 is the new API that will return all kind of signals, like the events or the stream. But what's returned can change at any time.

## Common parameters

Query parameters available for both endpoints.

### Format Type

Use to choose between the response format. Usually done with the `Content-Type` header but in this case we are using query parameters for legacy reason. This **could** change for the version V2 but this is not currently the case.

The `TEXT` format is dedicated to any client who can't handle easily parsing json. There is a difference of the separator use between the V1 and the V2 for enable more remove some restriction, see below.

**query parameter:** `format_type`

**possible values:** `JSON`, `TEXT`

**Default value:** See in the endpoints definitions below

### Communities

To filter signals per communities.

**query paramater:** `communities`

**possible values:** A list of string like `community1,community2`

**Default value:** `""` (Empty string)

## Dates

From receiving to sending/distribuing, including storing, signals time related information are in UTC.

We return the date in the following format: `%Y-%m-%dT%H:%M:%SZ` but keep in mind that even wihout the timezone expected the date to be UTC.

### V1

To avoid problem with existing clients the V1 date format output is `%Y/%m/%d %H:%M:%S+00:00`.

## Endpoints

### V1

!!! warning "Deprecated"

    But the one to use for now.

- `/v1/events`

#### Fields

The fields and the types available for this version of the API:

- **name** (_str_): The title (or title) of an event.
- **description** (_str_): The description of an event.
- **location_str** (_str_): The Resonite session ID or the name of the location of an event.
- **start_time** (_str_): The date and time of the beginning of an event. In the format `%Y/%m/%d %H:%M:%S+00:00`
- **end_time** (_str_): The date and time of the ending of an event. In the format `%Y/%m/%d %H:%M:%S+00:00`
- **community_name** (_str_): The name of the community of an event.

#### Format

##### TEXT

**Default:** True

Separators:

- Field separator: `` ` ``
- Row separator: `\n`

Example:

```
name`description`location`start_time`end_time`community_name\n
```

##### JSON

**Default:** False

### V2

!!! warning "Not Frozen"

    To use at your own risk.

- `/v2/events`

#### Fields

!!! warning "For the `TXT` format"

    The field order is different than the V1!

The fields and the types available for this version of the API (in the correct order for the `TXT` format):

- **name** (_str_): The title (or title) of an event.
- **description** (_str_): The description of an event.
- **session_image** (_str_): The image of an event.
- **location_str** (_str_): The Resonite session ID or the name of the location of an event.
- **location_web_session_url** (_str_): The Resonite session HTTP URL of the location of an event.
- **location_session_url** (_str_): The Resonite session URL of an event.
- **start_time** (_str_): The date and time of the beginning of an event. In the format `%Y/%m/%d %H:%M:%S+00:00`
- **end_time** (_str_): The date and time of the ending of an event. In the format `%Y/%m/%d %H:%M:%S+00:00`
- **community_name** (_str_): The name of the community of an event.
- **community_url** (_str_): The URL of the community of an event.
- **tags** (_str_): The tags of the community of an event.

#### Format

##### TEXT

**Default:** False

Separators:

- Field separator: `Record Separator (RS)` UTF-16: `001E`
- Row separator: `Group Separator (GS) ` UTF-16: `001D`

Example:

```
name<RS>description<RS>location<RS>start_time<RS>end_time<RS>community_name<RS>(...more fields go here)<GS>
```

!!! note

    `<RS>` and `<GS>` are **invisible** characters!

##### JSON

**Default:** True

#### Future planned

- `/v2/communities`: return the list of the communities available
- `/v2/signals`: return the list of signals
