import os

from django.conf import settings
from PIL import Image, UnidentifiedImageError


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def validate_uploaded_image(upload):
    """Return (ok, error) validating an uploaded file is a genuine image."""
    if not upload:
        return False, 'No file uploaded.'
    ext = os.path.splitext(upload.name)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        return False, 'Only image files (jpg, png, gif, webp) are allowed.'
    if upload.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        return False, f'File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.'
    try:
        image = Image.open(upload)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return False, 'The uploaded file is not a valid image.'
    finally:
        upload.seek(0)
    return True, None


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0
