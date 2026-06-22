"""Layer Flick Visibility - QGIS plugin entry point."""


def classFactory(iface):  # noqa: N802 (QGIS-required name)
    """Load the LayerFlickPlugin class.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .layer_flick_plugin import LayerFlickPlugin

    return LayerFlickPlugin(iface)
