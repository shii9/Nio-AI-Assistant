import requests
from PIL import Image
from io import BytesIO
import os
from time import sleep

# 🔑 Replace with your valid Hugging Face API token
HUGGINGFACE_API_KEY = "HUGGINGFACE_API_KEY"
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HEADERS = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

os.makedirs("Data", exist_ok=True)

def generate_image(prompt: str, index: int = 1):
    payload = {"inputs": prompt}

    print(f"🎨 Generating image {index}...")

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            filename = f"Data/{prompt.replace(' ', '_')}_{index}.png"
            image.save(filename)
            return filename
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print("❌ Exception while generating image:", e)
        return None

def main():
    prompt = input("Enter your prompt for generating the image:\n> ").strip()

    if not prompt:
        print("❗ Prompt cannot be empty.")
        return

    print("\n🚀 Generating images...")
    image_paths = []

    for i in range(1):  # You can change this number if needed
        img_path = generate_image(f"{prompt}, ultra realistic, 8k", i + 1)
        if img_path:
            image_paths.append(img_path)
        sleep(3)  # Add delay to avoid rate-limiting

    if image_paths:
        print(f"\n✅ Generated {len(image_paths)} image(s):")
        for path in image_paths:
            print(f"🖼️ Saved at: {path}")
            try:
                Image.open(path).show()
            except:
                print("❗ Could not open image viewer.")
    else:
        print("❌ Failed to generate any images.")

if __name__ == "__main__":
    main()
