"""Pruned CORE leaf: failure ledger + atomic store (stdlib only).

The parent tree's CORE package carries the memory bus, audit trail and
free-threading pools; none of that ships here. These two leaves are what
Eve's runners and shards actually import, and both degrade to a local
no-op when even this leaf is absent.
"""
