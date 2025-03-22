# Usage

The system is splited in different instances.

The first one will handle all the signals while the other will handle the clients, the HTTP API and the Website.

!!! danger

    All commands must be run in the folder `backend`.

!!! note

    As seen in the [configuration section](server-configuration.md) since the HTTP API require you to use `resonite-communities.local` for local development all link will use this, per convention.

## Signals manager

By default the system will run it's signals (both collectors and transmitters) at
at an interval of 5 minutes. See the [section about the architecture of the system](architecture.md)
for more information.

To start an instance of the signals manager use:

```console
poetry run signals_manager
```

## HTTP API

To start an instance of the HTTP API client use:

```console
poetry run api_client
```

Accessible at [http://resonite-communities.local:8000/](http://resonite-communities.local:8000/) and [http://private.resonite-communities.local:8000/](http://private.resonite-communities.local:8000/). See the [HTTP API section for more information](../ClientIntegration/http-api-usage.md).

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the HTTP API client will listen

## Website

To start an instance of the web client use:

```console
poetry run web_client
```

Accessible at [http://resonite-communities.local:8001/](http://resonite-communities.local:8001/).

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the Website client will listen

## Documentation

To start an instance of the documentation use:

```console
poetry run docs serve
```

Accessible at [http://resonite-communities.local:8002](http://resonite-communities.local:8002)

**Note:** You can use the option `-a <IP:PORT>` to change the host and port the Documentation will listen

## Tips

### Developing on another device that Resonite is running

In the case where you want to develop on a device you need to say to VSCode to listen to all interface.

Search for `Remote: Local Port Host` and set it to `allInterfaces`

### DIrect connection without port

Let's say you configure your hostfile like explained in [server-configuration](server-configuration.md) and you can access the service via `resonite-communities.local:8000` but you want to have access with `resonite-communities.local` directly without the port.

Depending of your operating system you will need help from other software to redirect everything that come to the port `80` (aka no port in the url) to the redirection automatically made by VSCode. Go into the `PORTS` forwading setting and vscode and for the `80` port take the `fowarded address` port.

#### Linux

For linux you can simply use a program called `socat` and use it that way:

```console
sudo socat TCP-LISTEN:80,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:44677 # Replace the last number with the forwarded address given by VSCode.
```

!!! danger

    This only work locally but not from the remote device, while `http://resonite-communities.local:8001` works this is not the case of `http://resonite-communities.local`

#### Windows

!!! warning

    Someone need to test on Windows.