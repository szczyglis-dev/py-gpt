"""Composed web renderer components, organized by responsibility.

Renderer exposes operations consumed by application clients and BaseRenderer.
Use component APIs directly for message construction, timelines and policies.
Methods accessed outside their owning class have public names; underscore-prefixed
helpers are local implementation details. Do not add facade delegates for them.
"""
