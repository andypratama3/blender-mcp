# Security Policy

## Threat model

The Blender MCP bridge executes **arbitrary Python inside Blender** with full `bpy`
access. Anyone who can reach the socket can read files the Blender process can read,
write files, and run system commands through Python. Treat the port as a local
administrative interface.

This repo adds clients, installers, and docs on top of that bridge. It does not add a
network service, telemetry, or remote endpoints.

## Safe defaults

- The bridge must stay bound to `127.0.0.1`. Never expose port `9876` to a LAN, a
  container network, or the public internet.
- Do not run a second MCP server on the same port.
- Review snippets before executing them, especially anything that imports `os`,
  `subprocess`, `shutil`, `socket`, or writes outside the project directory.
- Run Blender as your normal user, not as root/administrator.
- Keep the official add-on updated through Blender's extension manager.

## Reporting a vulnerability

Do **not** open a public issue for:

- a way to bypass the bridge sandbox,
- code execution outside the documented MCP flow,
- path traversal or file exfiltration in the installers or clients,
- credentials or personal data accidentally committed.

Report privately through GitHub Security Advisories:

<https://github.com/andypratama3/blender-mcp/security/advisories/new>

Include the affected file, version/commit, a minimal reproduction, and impact. You will
get an acknowledgement as soon as possible; please allow time for a fix before public
disclosure.

## Scope

In scope: `scripts/`, `skills/**/scripts/`, installers, CI workflows, docs that could
lead to unsafe operation.

Out of scope: vulnerabilities in Blender itself, in the official MCP add-on, or in
third-party skills you chose to install. Report those upstream.

## Supported versions

The `main` branch is supported. Tagged releases receive fixes when practical; there is
no long-term support commitment.
