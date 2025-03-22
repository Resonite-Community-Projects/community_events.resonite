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

#### Format

##### TEXT

**Default:** True

The field separator is done via the character `` ` `` while each row will be separated with `\n`.

For example, with only one event:

```
name`description`location`start_time`end_time`community_name\n
```

##### JSON

**Default:** False

### V2

!!! warning "Not Frozen"

    To use at your own risk.

- `/v2/events`

#### Format

##### TEXT

**Default:** False

##### JSON

**Default:** True

#### Future planned

- `/v2/communities`: return the list of the communities available
- `/v2/signals`: return the list of signals
