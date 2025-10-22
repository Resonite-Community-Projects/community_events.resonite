# Configurations Guide

To have your events pulled from our systems please check the systems below.

- [Discord event system](discord.md)
- [Hosted JSON File](hosted-JSON.md)

## Event Submission Guidelines

### Event Tagging Requirement

Since a source can contain events that take place in various locations, both virtually and physically, the keyword `Resonite` must be included in either the event's `title`, `description`, or `location`. This ensures your event is properly categorized and visible in the Resonite event calendar.

### Event Metadata (Discord Only)

For Discord events, you can add optional metadata to event descriptions to provide additional information. This metadata is automatically extracted and processed by the system, then removed from the displayed description.

#### Metadata Format

Metadata can be placed on any line but the line must only contain the metadata information using the following format:

```
+key:value
```

Each metadata line must:
- Start with a `+` character
- Be on its own line in description
- Follow the format `+key:value`

#### Supported Metadata Fields

**Language Specification**

Use `+language:` to specify which languages your event supports. You can list multiple languages separated by commas.

**Format:**
```
+language:en,es,fr
```

**Custom Tags**

Use `+tags:` to add custom tags to your event for better categorization.

**Format:**
```
+tags:beginner-friendly
```

#### Complete Example

Here's an example of a Discord event description with metadata:

```
Join us for a fun building session! We'll be creating cool things together.
All skill levels welcome!
+language:en,es
+tags:beginner-friendly
```

After processing, users will see:
```
Join us for a fun building session! We'll be creating cool things together.
All skill levels welcome!
```

And the event will be tagged with: `lang:en`, `lang:es`, and `beginner-friendly`.

#### Important Notes

- Metadata lines are automatically removed from the displayed description
- Metadata can be on any line but the complete line is treated as metadata information
- Invalid metadata lines are ignored
- Metadata processing is case-sensitive for keys (`+language:` not `+Language:`)

### Formatting Requirement

Before submitting your event, make sure to remove any new lines and certain special characters (`` ` ``) from your submission. This helps prevent formatting issues and ensures our event calendar functions smoothly when displaying your events.
