import cv2
import numpy as np
from PIL import Image
from scipy.spatial.distance import euclidean, cosine

def face_distance(known_embeddings, candidate_embedding, metric='euclidean'):
    if metric == 'euclidean':
        return np.linalg.norm(known_embeddings - candidate_embedding, axis=1)
    elif metric == 'cosine':
        return np.array([cosine(known, candidate_embedding) for known in known_embeddings])
    else:
        raise ValueError('Unknown metric')

def is_match(distances, threshold=0.6):
    return np.argmin(distances), np.min(distances) < threshold

# Error handling utility
def safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f'Error: {e}')
        return None

def prepare_image(image_input):
    """
    Converts input to a valid RGB image for face_recognition.

    Parameters:
    - image_input: Either a file path, OpenCV BGR image, or PIL Image

    Returns:
    - A valid RGB image (numpy array with dtype uint8)
    """
    # If the input is already a NumPy array (e.g., OpenCV BGR image)
    if isinstance(image_input, np.ndarray):
        if image_input.shape[-1] == 3:  # likely BGR
            img_rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
        elif len(image_input.shape) == 2:  # grayscale
            img_rgb = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
        else:
            raise ValueError("Unsupported image shape")
    # If the input is a PIL image
    elif isinstance(image_input, Image.Image):
        img_rgb = np.array(image_input.convert("RGB"))
    # If the input is a path string
    elif isinstance(image_input, str):
        img_bgr = cv2.imread(image_input)
        if img_bgr is None:
            raise ValueError(f"Image not found at {image_input}")
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    else:
        raise TypeError("Unsupported image input type")

    # Ensure dtype is uint8
    if img_rgb.dtype != np.uint8:
        img_rgb = img_rgb.astype(np.uint8)

    return img_rgb 