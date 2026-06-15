import os
import pickle
import numpy as np
from PIL import Image
import torch
import torchvision.models as models
from torchvision.models import ResNet18_Weights
import torchvision.transforms as transforms
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(title="Semantic Image Search Engine API")

# Enable CORS for development ease
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants & Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALLERY_DIR = os.path.join(BASE_DIR, "data", "gallery")
CACHE_FILE = os.path.join(BASE_DIR, "data", "embeddings.pkl")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Create directories if they do not exist
os.makedirs(GALLERY_DIR, exist_ok=True)
os.makedirs(FRONTEND_DIR, exist_ok=True)

# ----------------------------------------------------
# CNN Feature Extractor (PyTorch & ResNet-18)
# ----------------------------------------------------
device = torch.device("cpu")

# Image Preprocessing pipeline matches ResNet standard requirements
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# Global model holder
model = None

def get_model():
    global model
    if model is None:
        # Load weights and model
        weights = ResNet18_Weights.DEFAULT
        resnet = models.resnet18(weights=weights)
        # Remove final classification layer (fc) to extract the 512-dim output of the global pooling layer
        model = torch.nn.Sequential(*list(resnet.children())[:-1])
        model.to(device)
        model.eval()
    return model

def extract_features(image_path: str) -> np.ndarray:
    """Load an image, preprocess it, and run it through ResNet-18 to get a normalized 1D embedding vector."""
    try:
        img = Image.open(image_path).convert("RGB")
        img_tensor = preprocess(img).unsqueeze(0).to(device)
        
        net = get_model()
        with torch.no_grad():
            features = net(img_tensor)
            # Squeeze dimensions: (1, 512, 1, 1) -> (512,)
            features = torch.squeeze(features)
            # Convert to numpy and normalize to unit length for easier cosine similarity
            embedding = features.cpu().numpy()
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding
    except Exception as e:
        print(f"Error extracting features from {image_path}: {e}")
        return None

# ----------------------------------------------------
# Cache / Indexing System
# ----------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}. Reinitializing.")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
    except Exception as e:
        print(f"Error saving cache: {e}")

def index_gallery():
    """Scan the gallery folder, remove stale embeddings, and extract new ones."""
    print("Indexing image gallery...")
    cache = load_cache()
    
    # Get all valid image files in gallery
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    gallery_files = [
        f for f in os.listdir(GALLERY_DIR)
        if os.path.splitext(f.lower())[1] in valid_extensions
    ]
    
    updated_cache = {}
    needs_save = False
    
    # Extract features for new or modified files
    for filename in gallery_files:
        filepath = os.path.join(GALLERY_DIR, filename)
        mtime = os.path.getmtime(filepath)
        
        # Check if already cached and file has not changed
        if filename in cache and cache[filename].get("mtime") == mtime:
            updated_cache[filename] = cache[filename]
        else:
            print(f"Extracting features for {filename}...")
            embedding = extract_features(filepath)
            if embedding is not None:
                updated_cache[filename] = {
                    "mtime": mtime,
                    "embedding": embedding
                }
                needs_save = True
    
    # If cache size changed (e.g. deletions), we need to save
    if len(cache) != len(updated_cache):
        needs_save = True
        
    if needs_save:
        save_cache(updated_cache)
        print(f"Indexing complete. Cached {len(updated_cache)} images.")
    else:
        print("Gallery index is up to date.")
        
    return updated_cache

# Initialize index on startup
@app.on_event("startup")
def startup_event():
    # Pre-load model to warm up CPU memory
    get_model()
    index_gallery()

# ----------------------------------------------------
# API Endpoints
# ----------------------------------------------------

@app.get("/api/gallery")
def get_gallery():
    """Return all images currently in the gallery."""
    # Re-run index to catch any manual additions
    cache = index_gallery()
    images = []
    for filename in sorted(cache.keys()):
        images.append({
            "filename": filename,
            "url": f"/gallery/{filename}"
        })
    return {"images": images}

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload a new image to the gallery and trigger index update."""
    valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in valid_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")
        
    filepath = os.path.join(GALLERY_DIR, file.filename)
    try:
        with open(filepath, "wb") as f:
            f.write(await file.read())
        
        # Trigger index update
        index_gallery()
        return {"filename": file.filename, "url": f"/gallery/{file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {e}")

@app.post("/api/search")
async def search_similar(file: UploadFile = File(...)):
    """Upload a query image, compute its embedding, and find the top matches in the gallery."""
    # Temporarily save uploaded query image to extract features
    temp_query_path = os.path.join(BASE_DIR, "data", "temp_query" + os.path.splitext(file.filename)[1])
    try:
        with open(temp_query_path, "wb") as f:
            f.write(await file.read())
            
        # Extract features for query
        query_embedding = extract_features(temp_query_path)
        if query_embedding is None:
            raise HTTPException(status_code=400, detail="Could not extract features from the uploaded image.")
            
        # Load gallery cache
        cache = index_gallery()
        if not cache:
            return {"results": []}
            
        # Compute cosine similarity
        results = []
        for filename, data in cache.items():
            gallery_emb = data["embedding"]
            # Since both vectors are normalized, cosine similarity is just the dot product!
            sim = float(np.dot(query_embedding, gallery_emb))
            # Convert similarity (-1 to 1) to percentage score (0 to 100)
            score = max(0.0, (sim + 1.0) / 2.0) * 100.0
            
            results.append({
                "filename": filename,
                "url": f"/gallery/{filename}",
                "score": round(score, 2)
            })
            
        # Sort results by similarity descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return {"results": results[:12]} # Return top 12 matches
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    finally:
        # Cleanup temporary file
        if os.path.exists(temp_query_path):
            os.remove(temp_query_path)

@app.delete("/api/gallery/{filename}")
def delete_image(filename: str):
    """Delete an image from the gallery and rebuild the index."""
    filepath = os.path.join(GALLERY_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    try:
        os.remove(filepath)
        index_gallery()
        return {"detail": "Image deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {e}")

# ----------------------------------------------------
# Static Files & SPA Routing
# ----------------------------------------------------

# Serve gallery images
app.mount("/gallery", StaticFiles(directory=GALLERY_DIR), name="gallery")

# Serve frontend directory
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# Serve root page
@app.get("/")
def get_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
