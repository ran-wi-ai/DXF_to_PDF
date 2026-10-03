import io
import tempfile
import streamlit as st
import ezdxf
from ezdxf.bbox import extents
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.properties import LayoutProperties
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="CAD (DXF) to 1:1 Scale PDF Converter",
    page_icon="📐",
    layout="wide"
)

st.title("📐 DXF to 1:1 Scale PDF Converter")
st.write("Upload a DXF file to render and export to PDF with exact scale.")
st.write("ranjith.wijekoon@gmail.com")

# Sidebar Settings
st.sidebar.header("Scale & Unit Settings")
dxf_unit = st.sidebar.selectbox(
    "Drawing Units in DXF",
    ["Millimeters (mm)", "Meters (m)", "Inches (in)"],
    index=0
)

# Dark mode / Light mode toggle to fix invisible white line issue
color_theme = st.sidebar.selectbox(
    "Color Theme",
    ["Black Lines on White Paper", "White Lines on Black Paper", "CAD Native Colors"],
    index=0
)

# Unit conversion factors to inches
unit_scale_to_inches = {
    "Millimeters (mm)": 1.0 / 25.4,
    "Meters (m)": 1000.0 / 25.4,
    "Inches (in)": 1.0
}

uploaded_file = st.file_uploader("Choose a DXF file", type=["dxf"])

if uploaded_file is not None:
    try:
        # Save uploaded file to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        # Compute bounding box
        bbox = extents(msp)
        if not bbox.has_data:
            st.error("The DXF file appears to be empty or contains no valid geometry in Modelspace.")
            st.stop()

        min_x, min_y, _ = bbox.extmin
        max_x, max_y, _ = bbox.extmax

        width_units = max_x - min_x
        height_units = max_y - min_y

        if width_units <= 0 or height_units <= 0:
            st.error("Could not compute valid non-zero bounding box dimensions for this file.")
            st.stop()

        st.info(f"**Bounding Box Extents:** {width_units:.2f} × {height_units:.2f} drawing units")

        # Convert units to inches for PDF paper size
        scale_factor = unit_scale_to_inches[dxf_unit]
        pdf_width_in = width_units * scale_factor
        pdf_height_in = height_units * scale_factor

        st.write(f"**Target PDF Page Size (1:1 Scale):** {pdf_width_in:.2f} in × {pdf_height_in:.2f} in ({pdf_width_in * 25.4:.1f} mm × {pdf_height_in * 25.4:.1f} mm)")

        # Determine Background & Default Line Colors
        if "Black Lines" in color_theme:
            bg_color = "#FFFFFF"
            default_color = "#000000"
        elif "White Lines" in color_theme:
            bg_color = "#000000"
            default_color = "#FFFFFF"
        else:
            bg_color = "#FFFFFF"
            default_color = None

        # Setup Figure
        fig = plt.figure(figsize=(pdf_width_in, pdf_height_in), dpi=100)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(bg_color)
        fig.patch.set_facecolor(bg_color)

        # Context & Layout Properties setup to force high-visibility rendering
        ctx = RenderContext(doc)
        
        # Override default background / foreground colors if requested
        if default_color:
            layout_props = LayoutProperties.from_layout(msp)
            layout_props.set_colors(bg_color, default_color)
        else:
            layout_props = LayoutProperties.from_layout(msp)

        out = MatplotlibBackend(ax)
        frontend = Frontend(ctx, out)
        frontend.draw_layout(msp, layout_properties=layout_props, finalize=True)

        # Explicitly enforce coordinate limits matching the bounding box
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        # --- SAVE TO BUFFER BEFORE PREVIEW ---
        pdf_buffer = io.BytesIO()
        fig.savefig(
            pdf_buffer,
            format="pdf",
            bbox_inches="tight",
            pad_inches=0,
            facecolor=bg_color
        )
        pdf_buffer.seek(0)

        # Render preview in Streamlit
        st.subheader("Preview")
        st.pyplot(fig)
        plt.close(fig)

        # Download Button
        output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_1to1_scale.pdf"
        st.download_button(
            label="📥 Download 1:1 Scale PDF",
            data=pdf_buffer,
            file_name=output_filename,
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
