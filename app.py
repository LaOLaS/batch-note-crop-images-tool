import streamlit as st
from PIL import Image, ImageCms
import io
import zipfile
import os

# sRGB color profile
SRGB_PROFILE = ImageCms.createProfile("sRGB")

# Default crop values (in pixels) - change these as needed
DEFAULT_LEFT = 50
DEFAULT_TOP = 30
DEFAULT_BOTTOM = 30

st.set_page_config(page_title="Batch Image Cropper", layout="wide")
st.title("🖼️ Batch Image Cropper")
st.markdown("Upload images and crop a fixed amount from left, top, and bottom edges.")

# Crop settings in sidebar
st.sidebar.header("Crop Settings (pixels)")
left_crop = st.sidebar.number_input("Left", min_value=0, value=DEFAULT_LEFT, step=10)
top_crop = st.sidebar.number_input("Top", min_value=0, value=DEFAULT_TOP, step=10)
bottom_crop = st.sidebar.number_input("Bottom", min_value=0, value=DEFAULT_BOTTOM, step=10)

# File uploader
uploaded_files = st.file_uploader(
    "Upload images",
    type=["png", "jpg", "jpeg", "webp", "bmp"],
    accept_multiple_files=True
)

def crop_image(image: Image.Image, left: int, top: int, bottom: int) -> Image.Image:
    """Crop image by removing pixels from left, top, and bottom."""
    width, height = image.size
    
    # Calculate crop box (left, upper, right, lower)
    crop_box = (
        left,
        top,
        width,
        height - bottom
    )
    
    return image.crop(crop_box)

def get_format_from_filename(filename: str) -> str:
    """Get PIL format string from filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    format_map = {
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.png': 'PNG',
        '.webp': 'WEBP',
        '.bmp': 'BMP',
    }
    return format_map.get(ext, 'PNG')

def convert_to_srgb(image: Image.Image) -> Image.Image:
    """Convert image to sRGB color space."""
    # If image has an ICC profile, convert from it to sRGB
    if 'icc_profile' in image.info:
        try:
            input_profile = ImageCms.ImageCmsProfile(io.BytesIO(image.info['icc_profile']))
            image = ImageCms.profileToProfile(image, input_profile, SRGB_PROFILE)
        except Exception:
            pass  # If conversion fails, continue with original
    return image

def get_image_bytes(image: Image.Image, format: str = "PNG") -> bytes:
    """Convert PIL Image to bytes in sRGB color space."""
    buffer = io.BytesIO()

    # Convert to sRGB
    image = convert_to_srgb(image)

    # Get sRGB ICC profile bytes for embedding
    srgb_profile_bytes = ImageCms.ImageCmsProfile(SRGB_PROFILE).tobytes()

    if format == 'JPEG':
        # JPEG doesn't support transparency - convert RGBA/P to RGB
        if image.mode in ('RGBA', 'P', 'LA'):
            # Create white background and composite
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode in ('RGBA', 'LA'):
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert('RGB')
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        image.save(buffer, format='JPEG', quality=95, icc_profile=srgb_profile_bytes)
    else:
        # For PNG and other formats, embed sRGB profile
        image.save(buffer, format=format, icc_profile=srgb_profile_bytes)

    buffer.seek(0)
    return buffer.getvalue()

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} image(s) uploaded**")
    st.markdown(f"Crop settings: Left={left_crop}px, Top={top_crop}px, Bottom={bottom_crop}px")
    
    cropped_images = []
    
    # Process each image
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        original_size = image.size
        
        # Check if crop values are valid
        if left_crop >= original_size[0] or (top_crop + bottom_crop) >= original_size[1]:
            st.error(f"❌ {uploaded_file.name}: Crop values exceed image dimensions ({original_size[0]}x{original_size[1]})")
            continue
        
        cropped = crop_image(image, left_crop, top_crop, bottom_crop)
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
            img_format = get_format_from_filename(uploaded_file.name)
            img_bytes = get_image_bytes(cropped, format=img_format)
            mime_type = "image/jpeg" if img_format == "JPEG" else f"image/{img_format.lower()}"
            st.download_button(
                label=f"Download {uploaded_file.name}",
                data=img_bytes,
                file_name=f"cropped_{uploaded_file.name}",
                mime=mime_type
            )
    
    # Download all as ZIP
    if len(cropped_images) > 1:
        st.markdown("---")
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, img in cropped_images:
                img_format = get_format_from_filename(name)
                img_bytes = get_image_bytes(img, format=img_format)
                zf.writestr(f"cropped_{name}", img_bytes)
        
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 Download All as ZIP",
            data=zip_buffer.getvalue(),
            file_name="cropped_images.zip",
            mime="application/zip"
        )
