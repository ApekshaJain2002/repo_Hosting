import google.generativeai as genai
import os

# Load API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# List models
for model in genai.list_models():
    print(model.name, "->", model.supported_generation_methods)