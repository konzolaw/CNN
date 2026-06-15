import os
import requests
from PIL import Image, ImageDraw, ImageFont

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALLERY_DIR = os.path.join(BASE_DIR, "data", "gallery")
os.makedirs(GALLERY_DIR, exist_ok=True)

# Image URLs to seed our database (3 per category)
IMAGE_SEEDS = {
    "cat_1.jpg": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=400&q=80",
    "cat_2.jpg": "https://images.unsplash.com/photo-1519052537078-e6302a4968d4?auto=format&fit=crop&w=400&q=80",
    "cat_3.jpg": "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?auto=format&fit=crop&w=400&q=80",
    "dog_1.jpg": "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=400&q=80",
    "dog_2.jpg": "https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=400&q=80",
    "dog_3.jpg": "https://images.unsplash.com/photo-1534361960057-19889db9621e?auto=format&fit=crop&w=400&q=80",
    "forest_1.jpg": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=400&q=80",
    "forest_2.jpg": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=400&q=80",
    "forest_3.jpg": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=400&q=80",
    "city_1.jpg": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?auto=format&fit=crop&w=400&q=80",
    "city_2.jpg": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&q=80",
    "city_3.jpg": "https://images.unsplash.com/photo-1449034446853-66c86144b0ad?auto=format&fit=crop&w=400&q=80",
    "car_1.jpg": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=400&q=80",
    "car_2.jpg": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=400&q=80",
    "car_3.jpg": "https://images.unsplash.com/photo-1580273916550-e323be2ae537?auto=format&fit=crop&w=400&q=80"
}

def generate_fallback_image(filename: str):
    """Generate a colored geometric image if network download fails, ensuring different categories look distinct."""
    print(f"Generating fallback image for {filename}...")
    img = Image.new("RGB", (400, 400), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Customize based on category
    category = filename.split("_")[0]
    if category == "cat":
        # Draw soft warm circle
        draw.ellipse([80, 80, 320, 320], fill=(255, 179, 186), outline=(255, 100, 100), width=4)
        draw.polygon([(200, 150), (160, 220), (240, 220)], fill=(255, 120, 120))
        text = "Cat (Fallback)"
    elif category == "dog":
        # Draw cool blue rectangle
        draw.rectangle([80, 80, 320, 320], fill=(186, 225, 255), outline=(100, 150, 255), width=4)
        draw.ellipse([160, 160, 240, 240], fill=(100, 150, 255))
        text = "Dog (Fallback)"
    elif category == "forest":
        # Draw green triangles (trees)
        draw.rectangle([0, 0, 400, 400], fill=(200, 240, 200))
        draw.polygon([(200, 50), (100, 250), (300, 250)], fill=(46, 125, 50))
        draw.polygon([(200, 150), (120, 320), (280, 320)], fill=(27, 94, 32))
        text = "Forest (Fallback)"
    elif category == "city":
        # Draw grey building blocks
        draw.rectangle([0, 0, 400, 400], fill=(220, 220, 235))
        draw.rectangle([50, 150, 150, 400], fill=(120, 120, 140))
        draw.rectangle([180, 100, 280, 400], fill=(80, 80, 100))
        draw.rectangle([300, 200, 370, 400], fill=(150, 150, 170))
        text = "City (Fallback)"
    elif category == "car":
        # Draw red carriage and black wheels
        draw.rectangle([60, 200, 340, 300], fill=(255, 105, 97), outline=(200, 50, 50), width=4)
        draw.rectangle([120, 130, 280, 200], fill=(255, 105, 97), outline=(200, 50, 50), width=4)
        draw.ellipse([90, 280, 150, 340], fill=(50, 50, 50))
        draw.ellipse([250, 280, 310, 340], fill=(50, 50, 50))
        text = "Car (Fallback)"
    else:
        draw.rectangle([80, 80, 320, 320], fill=(255, 255, 186), outline=(200, 200, 100), width=4)
        text = "Image (Fallback)"

    # Draw label text
    draw.text((150, 20), text, fill=(50, 50, 50))
    
    filepath = os.path.join(GALLERY_DIR, filename)
    img.save(filepath)

def seed():
    print("Seeding gallery directory...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    
    for filename, url in IMAGE_SEEDS.items():
        filepath = os.path.join(GALLERY_DIR, filename)
        if os.path.exists(filepath):
            print(f"{filename} already exists. Skipping.")
            continue
            
        try:
            print(f"Downloading {filename}...")
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                print(f"Successfully downloaded {filename}")
            else:
                print(f"Failed to download {filename} (HTTP {response.status_code}). Using fallback.")
                generate_fallback_image(filename)
        except Exception as e:
            print(f"Network error downloading {filename}: {e}. Using fallback.")
            generate_fallback_image(filename)

if __name__ == "__main__":
    seed()
