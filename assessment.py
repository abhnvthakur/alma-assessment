from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import uuid
import tempfile
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re
import json
from pathlib import Path
import requests
from pydantic_settings import BaseSettings
from pydantic import Field
import nest_asyncio
import PyPDF2
from docx import Document
import google.generativeai as genai

app = FastAPI(title="O-1A Visa Assessment API")
GOOGLE_API_KEY = "enter_key"  # Replace with your actual API key

# Configure Gemini API
def setup_gemini_api():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is required")
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Test API connection
    try:
        models = genai.list_models()
        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        print(f"Available Gemini models: {available_models}")
        if not any('gemini-1.5-flash' in model for model in available_models):
            print("Warning: gemini-1.5-flash model not found in available models. Falling back to gemini-1.0-pro if available.")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to Gemini API: {e}")


executor = ThreadPoolExecutor(max_workers=os.cpu_count())


CRITERIA = {
    "awards": {
        "description": "Receipt of nationally or internationally recognized prizes or awards for excellence in the field of endeavor",
        "keywords": ["award", "prize", "recognition", "recipient", "winner", "finalist"]
    },
    "membership": {
        "description": "Membership in associations in the field for which classification is sought, which require outstanding achievements of their members, as judged by recognized national or international experts in their disciplines or fields",
        "keywords": ["member", "fellow", "association", "society", "institute", "organization"]
    },
    "press": {
        "description": "Published material about the alien in professional or major trade publications or other major media, relating to the alien's work in the field for which classification is sought",
        "keywords": ["featured", "article", "interview", "publication", "media", "press"]
    },
    "judging": {
        "description": "Participation, either individually or on a panel, as a judge of the work of others in the same or an allied field of specialization for which classification is sought",
        "keywords": ["judge", "reviewer", "panel", "evaluation", "committee", "assessment"]
    },
    "original_contribution": {
        "description": "Original scientific, scholarly, artistic, athletic, or business-related contributions of major significance in the field",
        "keywords": ["innovation", "developed", "created", "founded", "invented", "discovery"]
    },
    "scholarly_articles": {
        "description": "Authorship of scholarly articles in the field, in professional or major trade publications or other major media",
        "keywords": ["author", "publication", "journal", "paper", "research", "article"]
    },
    "critical_employment": {
        "description": "Employment in a critical or essential capacity for organizations and establishments that have a distinguished reputation",
        "keywords": ["lead", "director", "chief", "head", "manager", "executive", "founder"]
    },
    "high_remuneration": {
        "description": "Evidence that the alien has commanded a high salary or other significantly high remuneration for services, in relation to others in the field",
        "keywords": ["salary", "compensation", "income", "remuneration", "equity", "bonus"]
    }
}

#document extraction functions
def extract_text_from_pdf(file_path: str) -> str:
    text = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
    return "\n".join(text)

def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs if para.text)

def extract_text(file_path: str) -> str:
    """Extract text from PDF or DOCX files"""
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

def analyze_criteria_with_gemini(cv_text: str, criteria_name: str) -> Dict[str, Any]:
    """Use Gemini 2.0 Flash to analyze if CV content meets a specific criteria"""
    criteria_info = CRITERIA[criteria_name]
    

    keywords_str = ", ".join(criteria_info["keywords"])
    

prompt = f'''
    Analyze the following CV to determine if it meets the O-1A visa criterion:
    "{criteria_info['description']}"
    
    Relevant keywords: {keywords_str}
    
    CV content:
    {cv_text}
    
    Provide a JSON response with:
    1. "matches": [specific achievements that meet this criterion] - include at least 2-3 specific examples if they exist
    2. "met": true/false if criterion is met
    3. "confidence": score 0-1 indicating confidence
    
    Focus only on concrete evidence in the CV and be strict in your evaluation.
    Respond ONLY with valid JSON without any explanations before or after.
    '''
    

    try:
        # Get response from Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON response
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            text = response.text
            if '{' in text and '}' in text:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                json_str = text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                raise ValueError("No JSON found in response")
                
    except Exception as e:
        print(f"Error analyzing criteria {criteria_name}: {e}")
        return {
            "matches": [],
            "met": False,
            "confidence": 0.0,
            "error": f"Failed to parse response: {str(e)}"
        }


async def process_criteria(cv_text: str, criteria_name: str) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    

    criteria_result = await loop.run_in_executor(
        executor, analyze_criteria_with_gemini, cv_text, criteria_name
    )
    
    return criteria_result

@app.post("/api/v1/assessment/")
async def assess_cv(file: UploadFile = File(...)):
    """Process uploaded CV and assess against O-1A criteria"""

    if not file.filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")


    try:
        setup_gemini_api()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set up Gemini API: {str(e)}")


    temp_dir = tempfile.mkdtemp()
    try:

        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as buffer:
            contents = await file.read()
            buffer.write(contents)


        cv_text = extract_text(file_path)
        

        tasks = []
        for criteria_name in CRITERIA.keys():
            task = process_criteria(cv_text, criteria_name)
            tasks.append(task)
        

        criteria_results = await asyncio.gather(*tasks)
        

        results = {name: result for name, result in zip(CRITERIA.keys(), criteria_results)}
        

        criteria_met = sum(1 for c in results.values() if c.get("met", False))

        if criteria_met >= 5:
            qualification_rating = "high"
        elif criteria_met >= 3:
            qualification_rating = "medium"
        else:
            qualification_rating = "low"

        assessment = {
            "assessment_id": str(uuid.uuid4()),
            "criteria_results": results,
            "criteria_met": criteria_met,
            "qualification_rating": qualification_rating,
            "explanation": f"The candidate meets {criteria_met} out of 8 criteria required for O-1A visa qualification."
        }

        return JSONResponse(content=assessment)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        shutil.rmtree(temp_dir)


@app.get("/health")
async def health_check():
    """Check if the API is running and Gemini API is accessible"""
    try:
        setup_gemini_api()
        return {"status": "healthy", "message": "Service is running and Gemini API is accessible"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Service is running but Gemini API is not accessible: {str(e)}"}


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import uvicorn
    setup_gemini_api()  # Set up Gemini API before starting server
    uvicorn.run(app, host="0.0.0.0", port=8000)
