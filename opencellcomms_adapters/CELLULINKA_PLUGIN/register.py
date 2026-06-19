"""Plugin registry for the CELLULINKA_PLUGIN adapter.

Importing this module registers the adapter's functions via
@register_function. The engine discovers and imports it
automatically from opencellcomms_adapters/.
"""
from opencellcomms_adapters.CELLULINKA_PLUGIN.functions.initialization.ciao_cellulinka import ciao_cellulinka
