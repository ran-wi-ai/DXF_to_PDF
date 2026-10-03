import io
import tempfile
import streamlit as st
import ezdxf
from ezdxf.bbox import extents
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="CAD (DXF) to 1:1 Scale PDF Converter",
    page_icon="📐",
    layout="wide"
)

st.title("📐 DXF to 1:1 Scale PDF Converter")
st.write("Upload a DXF file to export a PDF preserving exact 1:1 drawing scale.")

# Sidebar Settings
st.sidebar.header("Scale & Unit Settings")
dxf_unit = st.sidebar.selectbox(
    "Drawing Units in DXF",
    ["Millimeters (mm)", "Meters (m)", "Inches (in)"],
    index=0
)

# Conversion factors to inches for PDF page sizing (1 inch = 25.4 mm)
unit_scale_to_inches = {
    "Millimeters (mm)": 1.0 / 25.4,
    "Meters (m)": 1000.0 / 25.4,
    "Inches (in)": 1.0
}

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
            st.error("The DXF file appears to be empty or contains no valid geometry.")
            st.stop()

        min_x, min_y, _ = bbox.extmin
        max_x, max_y, _ = bbox.extmax

        width_units = max_x - min_x
        height_units = max_y - min_y

        st.info(f"**Bounding Box Extents:** {width_units:.2f} × {height_units:.2f} drawing units")

        # Convert units to physical inches for 1:1 scale on PDF
        scale_factor = unit_scale_to_inches[dxf_unit]
        pdf_width_in = width_units * scale_factor
        pdf_height_in = height_units * scale_factor

        st.write(f"**Target PDF Page Size at 1:1 Scale:** {pdf_width_in:.2f} in × {pdf_height_in:.2f} in ({pdf_width_in * 25.4:.1f} mm × {pdf_height_in * 25.4:.1f} mm)")

        # Create Matplotlib Figure matching EXACT physical paper size
        fig = plt.figure(figsize=(pdf_width_in, pdf_height_in), dpi=72)
        ax = fig.add_axes([0, 0, 1, 1])  # Occupy 100% of the figure (no margins)

        # Render DXF Entities
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        # Lock limits strictly to bounding box for 1:1 ratio
        ax.set_xlim(min_x, max_x)
        ax.set_ylim(min_y, max_y)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        # --- EXPORT TO PDF BUFFER ---
        pdf_buffer = io.BytesIO()
        fig.savefig(
            pdf_buffer,
            format="pdf",
            bbox_inches=0,
            pad_inches=0,
            transparent=True
        )
        pdf_buffer.seek(0)

        # Show Preview
        st.subheader("Preview")
        st.pyplot(fig, clear_figure=False)
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
