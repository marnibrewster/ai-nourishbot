# tools_multimodal_open_source.py
import os
import json
import base64
import requests
from io import BytesIO
from typing import List, Optional
from langchain.tools import tool
import logging

logging.basicConfig(level=logging.INFO)
logging.info("Extracting ingredients from image...")

# ---------- Config ----------
BASE_URL = os.getenv("OPENAI_API_BASE", "http://localhost:8000/v1")
API_KEY  = os.getenv("OPENAI_API_KEY", "not-needed-for-local")
VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "meta-llama/Llama-3.2-90B-Vision-Instruct")
TEXT_MODEL   = os.getenv("OPENAI_TEXT_MODEL",   "qwen2.5-7b-instruct")

CHAT_COMPLETIONS_URL = f"{BASE_URL.rstrip('/')}/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def _b64_from_input(image_input: str) -> str:
    """Accepts URL or local path -> returns base64 data URI string."""
    if image_input.startswith("http"):
        resp = requests.get(image_input, timeout=30)
        resp.raise_for_status()
        data = resp.content
    else:
        if not os.path.isfile(image_input):
            raise FileNotFoundError(f"No file found at path: {image_input}")
        with open(image_input, "rb") as f:
            data = f.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"

def _chat(messages: list, model: str, max_tokens: int = 300) -> str:
    """Calls an OpenAI-compatible /chat/completions endpoint."""
    r = requests.post(
        CHAT_COMPLETIONS_URL,
        headers=HEADERS,
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"].strip()

# ---------- Tools ----------
class ExtractIngredientsTool:
    @tool("Extract ingredients")
    def extract_ingredient(image_input: str) -> str:
        """
        Extract ingredients from a food item image.
        :param image_input: Image file path (local) or URL (remote).
        :return: A string listing ingredients inferred from the image.
        """
        img_data_url = _b64_from_input(image_input)
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract ingredients from the food item image. Return a concise comma-separated list."},
                {"type": "image_url", "image_url": {"url": img_data_url}},
            ],
        }]
        return _chat(messages, model=VISION_MODEL, max_tokens=300)

class FilterIngredientsTool:
    @tool("Filter ingredients")
    def filter_ingredients(raw_ingredients: str) -> List[str]:
        """
        Processes the raw ingredient data and filters out non-food items or noise.
        :param raw_ingredients: Raw ingredients as a string.
        :return: List of cleaned ingredients.
        """
        ingredients = [ing.strip().lower() for ing in raw_ingredients.split(",") if ing.strip()]
        return ingredients

class NutrientAnalysisTool:
    @tool("Analyze nutritional values and calories of the dish from uploaded image")
    def analyze_image(image_input: str) -> str:
        """
        Provide a nutrient breakdown and total calories from the uploaded image.
        :param image_input: Image file path (local) or URL (remote).
        :return: Structured analysis string (identification, portions, totals, breakdown, evaluation, disclaimer).
        """
        img_data_url = _b64_from_input(image_input)
        assistant_prompt = """
You are an expert nutritionist. Analyze the food in the image and respond in this exact structure:

1. **Identification**: One item per line.
2. **Portion Size & Calorie Estimation**: Bullet each with: **[Food Item]**: [Portion], [Calories] calories
3. **Total Calories**: [Number]
4. **Nutrient Breakdown**: Key macros + notable micros per item and totals.
5. **Health Evaluation**: One paragraph.
6. **Disclaimer**:
The nutritional information and calorie estimates provided are approximate and are based on general food data. 
Actual values may vary depending on factors such as portion size, specific ingredients, preparation methods, and individual variations. 
For precise dietary advice or medical guidance, consult a qualified nutritionist or healthcare provider.
"""
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": assistant_prompt},
                {"type": "image_url", "image_url": {"url": img_data_url}},
            ],
        }]
        return _chat(messages, model=VISION_MODEL, max_tokens=700)
