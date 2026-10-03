import io
import tempfile
import streamlit as st
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt
from PIL import Image

st.set_page_config(
    page_title="CAD (DXF) to PDF/Image Converter",
    page_icon="📐",
    layout="wide"
)

st.title("📐 CAD File (DXF) to PDF / Image Converter")
st.write("Upload a DXF file to view, render, and export it to PDF, PNG, or JPG format.")

# Sidebar Controls
st.sidebar.header("Export Settings")
bg_color = st.sidebar.selectbox("Background Color", ["#FFFFFF (White)", "#000000 (Black)"], index=0)
bg_hex = "#FFFFFF" if "White" in bg_color else "#000000"

output_format = st.sidebar.radio("Output Format", ["PNG", "JPG", "PDF"])
dpi = st.sidebar.slider("DPI (Resolution)", min_value=100, max_value=600, value=300, step=50)

uploaded_file = st.file_uploader("Choose a DXF file", type=["dxf"])

if uploaded_file is not None:
    try:
        # Save uploaded file temporarily for ezdxf
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name

        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()

        st.success(f"File **{uploaded_file.name}** loaded successfully!")

        # Create Matplotlib Figure
        fig, ax = plt.subplots(figsize=(10, 10), dpi=dpi)
        ax.set_facecolor(bg_hex)
        fig.patch.set_facecolor(bg_hex)

        # Draw entities from DXF modelspace
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(msp, finalize=True)

        ax.autoscale()
        ax.set_aspect("equal", "datalim")
        ax.axis("off")

        # --- STEP 1: EXPORT TO BUFFER FIRST ---
        img_buffer = io.BytesIO()

        if output_format == "PDF":
            fig.savefig(img_buffer, format="pdf", bbox_inches="tight", pad_inches=0.1, facecolor=bg_hex)
            mime_type = "application/pdf"
            file_ext = "pdf"
        elif output_format == "PNG":
            fig.savefig(img_buffer, format="png", bbox_inches="tight", pad_inches=0.1, facecolor=bg_hex, dpi=dpi)
            mime_type = "image/png"
            file_ext = "png"
        else:  # JPG
            fig.savefig(img_buffer, format="png", bbox_inches="tight", pad_inches=0.1, facecolor=bg_hex, dpi=dpi)
            img_buffer.seek(0)
            pil_img = Image.open(img_buffer).convert("RGB")
            img_buffer = io.BytesIO()
            pil_img.save(img_buffer, format="JPEG", quality=95)
            mime_type = "image/jpeg"
            file_ext = "jpg"

        img_buffer.seek(0)

        # --- STEP 2: DISPLAY PREVIEW AFTER SAVING ---
        st.subheader("Preview")
        st.pyplot(fig, clear_figure=False)
        plt.close(fig)

        # --- STEP 3: DOWNLOAD BUTTON ---
        output_filename = f"{uploaded_file.name.rsplit('.', 1)[0]}_converted.{file_ext}"
        st.download_button(
            label=f"📥 Download converted {output_format}",
            data=img_buffer,
            file_name=output_filename,
            mime=mime_type
        )

    except Exception as e:
        st.error(f"Error processing DXF file: {e}")
