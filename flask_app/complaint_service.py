import os
import json
import google.generativeai as genai
from PIL import Image

# Configure Gemini API
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def analyze_complaint(image_path: str, text_description: str) -> dict:
    """
    Analyzes a complaint image and text to detect if it's a real issue or fake/spam.
    Uses Google Gemini Vision AI.
    """
    if not GENAI_API_KEY:
        # Mock response if no API key is set
        is_fake = "fake" in text_description.lower() or "selfie" in text_description.lower() or "meme" in text_description.lower() or "not match" in text_description.lower()
        score = 25.0 if is_fake else 85.0
        reasoning = (
            "This image appears to be unrelated to agriculture or is heavily edited." 
            if is_fake else 
            "The image and text seem highly correlated and depict a genuine issue."
        )
        return {
            "success": True,
            "is_fake": is_fake,
            "veracity_score": score,
            "category": "Irrelevant" if is_fake else "Pest Attack",
            "reasoning": f"This is a simulated analysis. {reasoning}",
            "priority": "Low" if is_fake else "High",
            "is_mock": True
        }

    try:
        genai.configure(api_key=GENAI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        img = Image.open(image_path)
        
        prompt = f"""
        You are an elite AI Verification System for agricultural complaints. 
        A farmer has submitted exactly one image and the following text description:
        "{text_description}"
        
        Your task is to:
        1. Compare the image with the text description to see if they match.
        2. Detect if the image is fake, AI-generated, irrelevant (e.g. a selfie, random internet meme), or a genuine agricultural issue (e.g., crop failure, pest attack, broken irrigation).
        3. Provide a Veracity Score (0 to 100) on how genuine this complaint is. Scores above 75 indicate a REAL complaint.
        4. Categorize the issue (ex: Water Issue, Pest Attack, Fertilizer Problem, Subsidies, etc.)
        5. Assign a priority: Low, Medium, High, or Urgent.
        
        Return the response AS A RAW JSON OBJECT (no markdown blocks or formatting around it) with these exact keys:
        {{
            "is_fake": true/false,
            "veracity_score": number (0-100),
            "category": "Issue category",
            "reasoning": "Detailed explanation of why it is real or fake based on visual evidence",
            "priority": "Low/Medium/High/Urgent"
        }}
        """
        
        response = model.generate_content([prompt, img])
        response_text = response.text.strip()
        
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        result = json.loads(response_text.strip())
        
        return {
            "success": True,
            "is_fake": result.get("is_fake", True),
            "veracity_score": result.get("veracity_score", 0),
            "category": result.get("category", "Unknown"),
            "reasoning": result.get("reasoning", ""),
            "priority": result.get("priority", "Low"),
            "is_mock": False
        }
        
    except Exception as e:
        print(f"Error during complaint verification: {e}")
        return {
            "success": False,
            "error": str(e)
        }
