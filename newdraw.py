from branca.element import Element, Figure, MacroElement
from jinja2 import Template

from folium.elements import JSCSSMixin

import folium

class NewDraw(JSCSSMixin, MacroElement):
    """
    Extension of vector drawing and editing plugin for Leaflet, which adds support for
    custom defined FeatureGroup to host drawings.

    Parameters
    ----------
    export : bool, default False
        Add a small button that exports the drawn shapes as a geojson file.
    filename : string, default 'data.geojson'
        Name of geojson file
    position : {'topleft', 'toprigth', 'bottomleft', 'bottomright'}
        Position of control.
        See https://leafletjs.com/reference.html#control
    show_geometry_on_click : bool, default True
        When True, opens an alert with the geometry description on click.
    draw_options : dict, optional
        The options used to configure the draw toolbar. See
        http://leaflet.github.io/Leaflet.draw/docs/leaflet-draw-latest.html#drawoptions
    edit_options : dict, optional
        The options used to configure the edit toolbar. See
        https://leaflet.github.io/Leaflet.draw/docs/leaflet-draw-latest.html#editpolyoptions

    Examples
    --------
    >>> m = folium.Map()
    >>> draw_group = folium.FeatureGroup(name='Drawings', control=True)
    >>> draw_group.add_to(m)
    >>> NewDraw(
    ...     edit_options={ 'featureGroup': draw_group.get_name()},
    ... ).add_to(m)

    For more info please check
    https://github.com/randyzwitch/streamlit-folium/issues/129

    """
    _template = Template(
        """
        {% macro script(this, kwargs) %}
            var options = {
                position: {{ this.position|tojson }},
                draw: {{ this.draw_options|tojson }},
                edit: {{ this.edit_options|tojson }},
            }
            
            var featureGroupName = options.edit.featureGroup;
            // This is the layer number of the FeatureGroup, which is set only if
            // the FeatureGroup has already been created.
            var layerNum = options.edit.layernum
            var drawnItems;

            // Find the layer
            if (layerNum !== undefined) {
                var count = 0;
                {{ this._parent.get_name() }}.eachLayer(function (layer) {
                    
                    if (layer instanceof L.FeatureGroup) {
                        if (count === layerNum) {
                            drawnItems = layer;
                        }
                        count++;
                    }
                });
            }

            // If no existing FeatureGroup was provided or found, create a new one.
            if (!drawnItems) {
                drawnItems = new L.FeatureGroup().addTo({{ this._parent.get_name() }});
                drawnItems.options.name = featureGroupName;
            }

            // Use the found or newly created FeatureGroup.
            options.edit.featureGroup = drawnItems;

            var {{ this.get_name() }} = new L.Control.Draw(
                options
            ).addTo( {{this._parent.get_name()}} );

            {{ this._parent.get_name() }}.on(L.Draw.Event.CREATED, function(e) {
                var layer = e.layer,
                    type = e.layerType;
                var coords = JSON.stringify(layer.toGeoJSON());
                {%- if this.show_geometry_on_click %}
                layer.on('click', function() {
                    alert(coords);
                    console.log(coords);
                });
                {%- endif %}
                drawnItems.addLayer(layer);
            });
            {{ this._parent.get_name() }}.on('draw:created', function(e) {
                drawnItems.addLayer(e.layer);
            });
            {% if this.export %}
            document.getElementById('export').onclick = function(e) {
                var data = drawnItems.toGeoJSON();
                var convertedData = 'text/json;charset=utf-8,'
                    + encodeURIComponent(JSON.stringify(data));
                document.getElementById('export').setAttribute(
                    'href', 'data:' + convertedData
                );
                document.getElementById('export').setAttribute(
                    'download', {{ this.filename|tojson }}
                );
            }
            {% endif %}
        {% endmacro %}
        """
    )

    default_js = [
        (
            "leaflet_draw_js",
            "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.2/leaflet.draw.js",
        )
    ]
    default_css = [
        (
            "leaflet_draw_css",
            "https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.2/leaflet.draw.css",
        )
    ]

    def __init__(
        self,
        export=False,
        filename="data.geojson",
        position="topleft",
        show_geometry_on_click=True,
        draw_options=None,
        edit_options=None,
    ):
        super().__init__()
        self._name = "DrawControl"
        self.export = export
        self.filename = filename
        self.position = position
        self.show_geometry_on_click = show_geometry_on_click
        self.draw_options = draw_options or {}
        self.edit_options = edit_options or {}

    def render(self, **kwargs):
        # Get all the layers to find the number of the featureGroup whose name
        # is given in edit_options['featureGroup'].
        # The solution is quite hacky, since it uses _children, which is
        # supposed to be private.

        figure = self.get_root()
        assert isinstance(
            figure, Figure
        ), "You cannot render this Element if it is not in a Figure."

        if ('featureGroup' in self.edit_options):
            map = next(iter(figure._children.values()))

            # We count only the FeatureGroups. We do so becasue after rendering 
            # the map will count among the layers also things like Markers.
            # That would make the layer count inconsistent between python and js. 
            layers = [fg for (fg, obj) in map._children.items() if isinstance(obj, folium.FeatureGroup)]
            layer_num = False
            for i, layer in enumerate(layers):
                print(layer)
                if layer == self.edit_options['featureGroup']:
                    layer_num = i
                    break
            if layer_num is not False:
                # We set a new edit_option, which is then used in _template
                print('Setting layer number to ' + str(layer_num))
                self.edit_options['layernum'] = layer_num

        super().render(**kwargs)

        export_style = """
            <style>
                #export {
                    position: absolute;
                    top: 5px;
                    right: 10px;
                    z-index: 999;
                    background: white;
                    color: black;
                    padding: 6px;
                    border-radius: 4px;
                    font-family: 'Helvetica Neue';
                    cursor: pointer;
                    font-size: 12px;
                    text-decoration: none;
                    top: 90px;
                }
            </style>
        """
        export_button = """<a href='#' id='export'>Export</a>"""
        if self.export:
            figure.header.add_child(Element(export_style), name="export")
            figure.html.add_child(Element(export_button), name="export_button")