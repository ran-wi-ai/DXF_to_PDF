import io
import tempfile
import matplotlib.pyplot as plt
from PIL import Image
import streamlit as st

import ezdxf
from ezdxf import options
from ezdxf.addons import text2path
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.bbox import extents

options.load_text_layout = True

# ... [Keep your Streamlit UI & file uploader code standard] ...

if uploaded_file is not None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        # --- CRITICAL FIX: CONVERT ALL TEXT / MTEXT TO VECTOR PATHS ---
        # Explode TEXT and MTEXT entities into paths so they render as geometry
        text_entities = msp.query("TEXT MTEXT")
        for entity in text_entities:
            try:
                paths = text2path.make_paths_from_entity(entity)
                for path in paths:
                    # Convert path to polylines/hatches in modelspace
                    text2path.explode(msp, entity)
                    break
                # Remove original text entity to avoid duplicate bounding boxes
                msp.delete_entity(entity)
            except Exception:
                pass  # Fall back gracefully if a specific entity fails conversion

        # Recalculate bounding box after text path expansion
        bbox = extents(msp)
        if not bbox.has_data:
            st.error("The DXF file appears to be empty or contains no valid geometry.")
            st.stop()

        min_x, min_y, _ = bbox.extmin
        max_x, max_y, _ = bbox.extmax

        width_units = max_x - min_x
        height_units = max_y - min_y

        # Setup plot dimensions and rendering context
        scale_factor = unit_scale_to_inches[dxf_unit]
        pdf_width_in = width_units * scale_factor
        pdf_height_in = height_units * scale_factor

        if "Black Lines" in color_theme:
            bg_color = "#FFFFFF"
            default_color = "#000000"
        elif "White Lines" in color_theme:
            bg_color = "#000000"
            default_color = "#FFFFFF"
        else:
            bg_color = "#FFFFFF"
            default_color = None

        fig = plt.figure(figsize=(pdf_width_in, pdf_height_in), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(bg_color)
        fig.patch.set_facecolor(bg_color)

        ctx = RenderContext(doc)
        layout_props = LayoutProperties.from_layout(msp)
        if default_color:
            layout_props.set_colors(bg_color, default_color)

        drawing_config = Configuration.defaults()

        out = MatplotlibBackend(ax)
        frontend = Frontend(ctx, out, config=drawing_config)
        frontend.draw_layout(msp, layout_properties=layout_props, finalize=True)

        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        # [Proceed with export buffer & download buttons...]
