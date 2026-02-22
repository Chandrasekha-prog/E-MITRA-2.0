import os
import google.generativeai as genai
from PIL import Image

# Configure Gemini API
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def analyze_plant_disease(image_path: str) -> dict:
    """
    Analyzes a plant leaf image to detect the plant type and any diseases.
    Uses Google Gemini Vision AI.
    """
    if not GENAI_API_KEY:
        # Mock response if no API key is set for immediate UI testing
        return {
            "success": True,
            "plant_type": "Unknown Leaf (Mock Mode)",
            "disease_detected": True,
            "disease_name": "Sample Blight (Mock Data)",
            "description": "This is a simulated analysis because no GEMINI_API_KEY was found in your environment variables. The leaf appears to have brown spots characteristic of early blight.",
            "recommendation": "Remove affected leaves and apply a copper-based fungicide. Avoid overhead watering.",
            "is_mock": True
        }

    try:
        genai.configure(api_key=GENAI_API_KEY)
        
        # Using a faster, higher-quota model to avoid rate limiting
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        img = Image.open(image_path)
        
        prompt = """
        You are an elite, highly experienced agricultural plant pathologist and botanist. 
        Perform the highest possible accuracy classification on this image of a plant/leaf.
        Provide the following information clearly structured:
        1. Plant Type: What plant is this? (Include precise scientific name)
        2. Health Status: Is it healthy or diseased?
        3. Disease Name: (If diseased, state the specific highest-classification disease name and pathogen, otherwise say 'None')
        4. Description: Provide a detailed, highly accurate scientific description of the visual symptoms you see.
        5. Treatment Recommendation: Provide advanced, highly effective practical agricultural advice to treat or manage this condition.
        
        Return the response AS A RAW JSON OBJECT (no markdown blocks or formatting around it) with these exact keys:
        {
            "plant_type": "name of plant",
            "is_healthy": true/false,
            "disease_name": "name of disease if any",
            "description": "description of symptoms",
            "recommendation": "treatment advice"
        }
        """
        
        response = model.generate_content([prompt, img])
        response_text = response.text.strip()
        
        # Clean up markdown if the model wrapped it in ```json ... ```
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        import json
        result = json.loads(response_text.strip())
        
        return {
            "success": True,
            "plant_type": result.get("plant_type", "Unknown"),
            "disease_detected": not result.get("is_healthy", True),
            "disease_name": result.get("disease_name", "None"),
            "description": result.get("description", ""),
            "recommendation": result.get("recommendation", ""),
            "is_mock": False
        }
        
    except Exception as e:
        print(f"Error during AI vision analysis: {e}")
        return {
            "success": False,
            "error": str(e)
        }
