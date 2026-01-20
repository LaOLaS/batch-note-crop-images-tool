import streamlit as st
from PIL import Image
import io
import zipfile

# Default crop values (in pixels) - change these as needed
DEFAULT_LEFT = 170
DEFAULT_RIGHT = 0
DEFAULT_TOP = 160
DEFAULT_BOTTOM = 160

st.set_page_config(page_title="Batch Image Cropper", layout="wide")
st.title("🖼️ Batch Image Cropper")
st.markdown("Upload images and crop a fixed amount from all edges.")

# Crop settings in sidebar
st.sidebar.header("Crop Settings (pixels)")
left_crop = st.sidebar.number_input("Left", min_value=0, value=DEFAULT_LEFT, step=10)
right_crop = st.sidebar.number_input("Right", min_value=0, value=DEFAULT_RIGHT, step=10)
top_crop = st.sidebar.number_input("Top", min_value=0, value=DEFAULT_TOP, step=10)
bottom_crop = st.sidebar.number_input("Bottom", min_value=0, value=DEFAULT_BOTTOM, step=10)

# File uploader
uploaded_files = st.file_uploader(
    "Upload images (you can add from multiple folders)",
    type=["png", "jpg", "jpeg", "webp", "bmp"],
    accept_multiple_files=True
)

def crop_image(image: Image.Image, left: int, right: int, top: int, bottom: int) -> Image.Image:
    """Crop image by removing pixels from all sides."""
    width, height = image.size
    
    # Calculate crop box (left, upper, right, lower)
    crop_box = (
        left,
        top,
        width - right,
        height - bottom
    )
    
    return image.crop(crop_box)

def get_image_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL Image to bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return buffer.getvalue()

# Initialize session state for processing
if "process_images" not in st.session_state:
    st.session_state.process_images = False

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} image(s) uploaded**")
    st.markdown(f"Crop settings: Left={left_crop}px, Right={right_crop}px, Top={top_crop}px, Bottom={bottom_crop}px")
    
    # Show uploaded file names
    with st.expander("Uploaded files", expanded=False):
        for f in uploaded_files:
            st.text(f"• {f.name}")
    
    st.markdown("---")
    
    # Crop button
    if st.button("🔪 CROP ALL IMAGES", type="primary", use_container_width=True):
        st.session_state.process_images = True
    
    # Process images only when button is clicked
    if st.session_state.process_images:
        cropped_images = []
        
        # Process each image
        for uploaded_file in uploaded_files:
            image = Image.open(uploaded_file)
            original_size = image.size
            
            # Check if crop values are valid
            if (left_crop + right_crop) >= original_size[0] or (top_crop + bottom_crop) >= original_size[1]:
                st.error(f"❌ {uploaded_file.name}: Crop values exceed image dimensions ({original_size[0]}x{original_size[1]})")
                continue
            
            cropped = crop_image(image, left_crop, right_crop, top_crop, bottom_crop)
            cropped_images.append((uploaded_file.name, cropped))
            
            # Display original and cropped side by side
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.caption(f"Original ({original_size[0]}x{original_size[1]})")
                    st.image(image, use_container_width=True)
                
                with col2:
                    new_size = cropped.size
                    st.caption(f"Cropped ({new_size[0]}x{new_size[1]})")
                    st.image(cropped, use_container_width=True)
                
                # Individual download button
                img_bytes = get_image_bytes(cropped)
                st.download_button(
                    label=f"Download {uploaded_file.name}",
                    data=img_bytes,
                    file_name=f"cropped_{uploaded_file.name}",
                    mime="image/png",
                    key=f"download_{uploaded_file.name}"
                )
        
        # Download all as ZIP
        if len(cropped_images) > 1:
            st.markdown("---")
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, img in cropped_images:
                    img_bytes = get_image_bytes(img)
                    zf.writestr(f"cropped_{name}", img_bytes)
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📦 Download All as ZIP",
                data=zip_buffer.getvalue(),
                file_name="cropped_images.zip",
                mime="application/zip",
                key="download_zip"
            )
        
        # Reset button
        if st.button("🔄 Reset and crop again"):
            st.session_state.process_images = False
            st.rerun()

else:
    st.info("👆 Upload images to get started. You can add images from different folders before processing.")
