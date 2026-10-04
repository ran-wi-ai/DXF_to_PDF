import io
import tempfile
import matplotlib.pyplot as plt
from PIL import Image
import streamlit as st

import ezdxf
from ezdxf import options
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.bbox import extents
from ezdxf.fonts import font_manager

# --- CRITICAL FIX FOR TEXT/MTEXT BOX ISSUE ---
options.load_text_layout = True

# Map missing/CAD fonts (e.g., txt.shx, simplex.shx) to system TTF fonts (e.g., Arial / Sans-Serif)
font_manager.load()
# Fallback font mapping when SHX/CAD fonts are not natively installed
font_manager.has_font("arial.ttf")

st.set_page_config(
    page_title="CAD (DXF) to PDF / Image Converter",
    page_icon="📐",
    layout="wide"
)

st.title("📐 DXF to PDF / Image Converter")
st.write("Upload a DXF file to view and export to PDF (1:1 scale), PNG, or JPG format.")

# Sidebar Settings for Fine-Tuning
st.sidebar.header("Advanced Settings")

dxf_unit = st.sidebar.selectbox(
    "Drawing Units in DXF",
    ["Millimeters (mm)", "Meters (m)", "Inches (in)"],
    index=0
)

dpi = st.sidebar.slider("DPI (Resolution for PNG/JPG)", min_value=100, max_value=600, value=300, step=50)

color_theme = st.sidebar.selectbox(
    "Color Theme",
    ["Black Lines on White Background", "White Lines on Black Background", "CAD Native Colors"],
    index=0
)

# Conversion factors to inches for physical paper/canvas sizing
unit_scale_to_inches = {
    "Millimeters (mm)": 1.0 / 25.4,
    "Meters (m)": 1000.0 / 25.4,
    "Inches (in)": 1.0
}

# Top Main Section - Explicit Container for Radio Controls
with st.container():
    st.subheader("1. Select Output Format")
    output_format = st.radio(
        label="Format",
        options=["PDF", "PNG", "JPG"],
        index=0,
        horizontal=True,
        key="output_format_radio"
    )

st.subheader("2. Upload DXF File")
uploaded_file = st.file_uploader("Choose a DXF file", type=["dxf"])

if uploaded_file is not None:
    try:
        # Save temporary DXF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        # Compute bounding box of entities in modelspace
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

        # Convert units to physical inches for 1:1 scale
        scale_factor = unit_scale_to_inches[dxf_unit]
        pdf_width_in = width_units * scale_factor
        pdf_height_in = height_units * scale_factor

        st.write(f"**Target Dimensions (1:1 Scale):** {pdf_width_in:.2f} in × {pdf_height_in:.2f} in ({pdf_width_in * 25.4:.1f} mm × {pdf_height_in * 25.4:.1f} mm)")

        # Determine Background & Line Colors
        if "Black Lines" in color_theme:
            bg_color = "#FFFFFF"
            default_color = "#000000"
        elif "White Lines" in color_theme:
            bg_color = "#000000"
            default_color = "#FFFFFF"
        else:
            bg_color = "#FFFFFF"
            default_color = None

        # Setup Figure matching exact drawing physical aspect ratio
        fig = plt.figure(figsize=(pdf_width_in, pdf_height_in), dpi=dpi)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(bg_color)
        fig.patch.set_facecolor(bg_color)

        # Context setup with Font Support
        ctx = RenderContext(doc)
        
        layout_props = LayoutProperties.from_layout(msp)
        if default_color:
            layout_props.set_colors(bg_color, default_color)

        # --- ENABLE TEXT RENDERING IN CONFIGURATION ---
        drawing_config = Configuration.defaults()
        # Force text rendering instead of raw boundary boxes
        drawing_config = drawing_config.with_changes(
            text_policy="filled"  # Options: "filled" (renders actual characters), "outline", or "box"
        )

        out = MatplotlibBackend(ax)
        frontend = Frontend(ctx, out, config=drawing_config)
        frontend.draw_layout(msp, layout_properties=layout_props, finalize=True)

        # Explicitly enforce coordinate limits matching the bounding box
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        # --- EXPORT TO BUFFER BEFORE PREVIEW ---
        export_buffer = io.BytesIO()

        if output_format == "PDF":
            fig.savefig(
                export_buffer,
                format="pdf",
                bbox_inches="tight",
                pad_inches=0,
                facecolor=bg_color
            )
            mime_type = "application/pdf"
            file_ext = "pdf"

        elif output_format == "PNG":
            fig.savefig(
                export_buffer,
                format="png",
                bbox_inches="tight",
                pad_inches=0,
                facecolor=bg_color,
                dpi=dpi
            )
            mime_type = "image/png"
            file_ext = "png"

        else:  # JPG
            fig.savefig(
                export_buffer,
                format="png",
                bbox_inches="tight",
                pad_inches=0,
                facecolor=bg_color,
                dpi=dpi
            )
            export_buffer.seek(0)
            pil_img = Image.open(export_buffer).convert("RGB")
            export_buffer = io.BytesIO()
            pil_img.save(export_buffer, format="JPEG", quality=95)
            mime_type = "image/jpeg"
            file_ext = "jpg"

        export_buffer.seek(0)

        # --- RENDER PREVIEW IN STREAMLIT ---
        st.subheader("3. Preview")
        st.pyplot(fig)
        plt.close(fig)

        # --- DOWNLOAD BUTTON ---
        clean_name = uploaded_file.name.rsplit('.', 1)[0]
        output_filename = f"{clean_name}_converted.{file_ext}"

        st.download_button(
            label=f"📥 Download {output_format}",
            data=export_buffer,
            file_name=output_filename,
            mime=mime_type
        )

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
