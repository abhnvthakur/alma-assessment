# Alma Assessment

A FastAPI application that analyzes CVs against O-1A visa criteria using Google's Gemini to provide a preliminary assessment of an applicant's qualification.

## Project Overview

This application was developed to help assess whether an individual meets the requirements for an O-1A immigration visa. The O-1A visa is for individuals who possess extraordinary ability in sciences, arts, education, business, or athletics.

The application:
1. Accepts a CV/resume in PDF or DOCX format
2. Analyzes the document against the 8 O-1A criteria
3. Identifies specific accomplishments that satisfy each criterion
4. Provides an overall qualification rating (low, medium, high)

## O-1A Visa Criteria

The application evaluates CVs against these eight criteria:

1. **Awards**: Receipt of nationally or internationally recognized prizes or awards for excellence in the field of endeavor
2. **Membership**: Membership in associations that require outstanding achievements of their members, as judged by recognized experts
3. **Press**: Published material about the applicant in professional or major trade publications, relating to their work
4. **Judging**: Participation as a judge of the work of others in the same or allied field
5. **Original Contribution**: Original scientific, scholarly, artistic, athletic, or business-related contributions of major significance
6. **Scholarly Articles**: Authorship of scholarly articles in the field, in professional publications or other major media
7. **Critical Employment**: Employment in a critical or essential capacity for organizations with a distinguished reputation
8. **High Remuneration**: Evidence of commanding a high salary or significant remuneration compared to others in the field

## System Design

The application follows the following flow:

1. **Input Processing**: Accepts and processes CV files through a FastAPI endpoint
2. **Text Extraction**: Extracts text content from PDF or DOCX files
3. **Parallel Analysis**: Analyzes the CV against each criterion concurrently using ThreadPoolExecutor
4. **AI Evaluation**: Utilizes Google's Gemini 1.5 Flash model to evaluate each criterion
5. **Response Generation**: Compiles results and generates an overall assessment

### Technology Stack

- **FastAPI**: Web framework for building the API
- **Google Generative AI (Gemini)**: AI model for document analysis
- **PyPDF2 & python-docx**: For document text extraction
- **asyncio & ThreadPoolExecutor**: For concurrent processing

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd o1a-visa-assessment-api
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install fastapi uvicorn python-multipart pydantic-settings PyPDF2 python-docx google-generativeai nest-asyncio
   ```

   Or create a `requirements.txt` file with the above dependencies and run:
   ```bash
   pip install -r requirements.txt
   ```

4. **Important**: Set up your Gemini API key
   - Obtain a Google Gemini API key from the [Google AI Studio](https://makersuite.google.com/)
   - Open the main Python file and replace the placeholder:
   ```python
   GOOGLE_API_KEY = "your-actual-gemini-api-key"  # Replace with your actual API key
   ```
   **Note**: For production, consider using environment variables instead of hardcoding the API key.

## Running the Application

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

You can also access the auto-generated documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### POST /api/v1/assessment/

Upload a CV for assessment.

**Request**:
- `file`: PDF or DOCX file (required)

**Response**: (for the sample_cv in the repo)
```json
{
    "assessment_id": "3a8d4189-9a05-4a35-bd24-b1f22362080d",
    "criteria_results": {
        "awards": {
            "matches": [
                "Gold - Math Olympiad IIT Kharagpur",
                "Gold - Team Member - DevRev High Prep Event IIT Madras",
                "Silver - Team Captain - ISRO High Prep Event IIT Bombay"
            ],
            "met": true,
            "confidence": 0.8
        },
        "membership": {
            "matches": [],
            "met": false,
            "confidence": 0.95
        },
        "press": {
            "matches": [],
            "met": false,
            "confidence": 0.95
        },
        "judging": {
            "matches": [],
            "met": false,
            "confidence": 0.9
        },
        "original_contribution": {
            "matches": [
                "Implemented Multi-Scale Feature Fusion, CoordConv, and adversarial training utilizing the Fast Gradient Sign Method in NovaNet, a novel method for enhanced pothole detection.",
                "Developed a method to rank topics based on preference weights in a semantic analysis project to determine citizens’ voting preferences.",
                "Built a custom prompting template, reducing overall token costs by 30% in a project focused on prompt compression and evaluation of RAG-based models."
            ],
            "met": true,
            "confidence": 0.7
        },
        "scholarly_articles": {
            "matches": [
                "RTaC: A Generalised Framework for Tooling",
                "NovaNet: A Novel Method for Enhanced Pothole Detection"
            ],
            "met": true,
            "confidence": 0.8
        },
        "critical_employment": {
            "matches": [
                "Advisor/Executive Head of Kharagpur Data Analytics Group, conducting national level hackathons and bootcamps, achieving an 82% YoY participation increase in Kharagpur Data Science Hackathon with over 5500 unique participants",
                "Senate Member/General Secretary Technology of Acharya Jagadish Chandra Bose Hall of Residence, coordinating technology activities and managing INR 200,000 in funds",
                "Lead 10 teams of over 100 members across Inter-Hall events such as Biz-Tech Quiz, Case Study and Data Hackathon"
            ],
            "met": true,
            "confidence": 0.8
        },
        "high_remuneration": {
            "matches": [],
            "met": false,
            "confidence": 0.95
        }
    },
    "criteria_met": 4,
    "qualification_rating": "medium",
    "explanation": "The candidate meets 4 out of 8 criteria required for O-1A visa qualification."
}
```

### GET /health

Check if the API is running and the Gemini API is accessible.

**Response**:
```json
{
  "status": "healthy",
  "message": "Service is running and Gemini API is accessible"
}
```

## Design Choices and Implementation Details

### Text Extraction

The application can extract text from both PDF and DOCX files using PyPDF2 and python-docx libraries, allowing for flexibility in document formats.

### Model Selection

Google's Gemini 1.5 Flash model was chosen for its:
- Ability to understand complex text
- Speed and efficiency for analyzing documents
- JSON output format capabilities
- Reliability in understanding domain-specific content

### Concurrent Processing

Each criterion is evaluated concurrently using ThreadPoolExecutor and asyncio to improve performance, especially when analyzing lengthy documents.

### Evaluation Rating System

The qualification rating is determined by:
- High: 5 or more criteria met
- Medium: 3-4 criteria met
- Low: 0-2 criteria met

This matches the general understanding that meeting 3 of the 8 criteria is typically sufficient for consideration, though meeting more strengthens the case.

## Evaluating Results

The API provides detailed information for each criterion:
- **Matches**: Specific accomplishments from the CV that satisfy the criterion
- **Met**: Boolean indicator of whether the criterion is satisfied
- **Confidence**: A score from 0 to 1 indicating the AI's confidence in its assessment

When evaluating results:
1. Focus on criteria with high confidence scores
2. Verify the specific matches against the actual CV content
3. Use the overall qualification rating as a preliminary assessment, not a final determination

**Important**: This tool provides a preliminary assessment only and should not replace professional legal advice from an immigration attorney.

## Limitations

- The assessment depends on information explicitly stated in the CV
- Results may vary based on how well the CV articulates achievements
- Technical terminology and domain-specific language may impact accuracy
- The AI model may occasionally misinterpret complex achievements
