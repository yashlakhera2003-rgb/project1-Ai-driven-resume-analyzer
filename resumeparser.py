import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field

load_dotenv()
my_api_key=os.getenv("GROQ_API_KEY")

if not my_api_key:
    raise ValueError("API key kaha hai bhai")

client=Groq(api_key=my_api_key)
model = "openai/gpt-oss-120b"



class JobD(BaseModel):
    role: str
    required_skills: list[str]
    preferred_skills: list[str]
    minimum_experience: float | None
    education_requirements: list[str]
    responsibilities: list[str]

# job description ka schema bna liya (json format me)....

def parse_job_description(job_description):

    jobd_schema = JobD.model_json_schema()

    system_prompt = f"""
    You are an expert HR assistant.

    Your job is to analyze job descriptions and extract
    structured information from them.

    Return ONLY valid JSON matching this schema:

    {jobd_schema}

    IMPORTANT:
    Do NOT return the schema itself.
    Do NOT return fields like "properties", "title" or "type".
    Fill the schema with actual information extracted from
    the job description.

    If minimum experience is not mentioned, return null.
    If information for a list is missing, return an empty list.
    Do not invent information.
    """

    user_prompt = f"""
    Analyze the following job description:

    {job_description}
    """

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]

    response_format = {
        "type": "json_object"
    }

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format
    )

    raw_json = response.choices[0].message.content

    job_data = json.loads(raw_json)

    job = JobD(**job_data)

    return job


class MatchResult(BaseModel):
    score: float
    details: dict

class Experience(BaseModel):

    # none=none means -> ye fields optional hai mandatory nhi hai to agr ye fields resume me nhi hongi to error nhi ayega...
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = []

class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience_years: float | None = None

    skills: list[str] = []
    experiences: list[Experience] = []
    education: list[str] = []
    projects: list[str] = []
    certifications: list[str] = []

resume_schema = Resume.model_json_schema()




#  PART-3 (RESUME PARSE KRRE HAI JO INFO CHAHIYE RESUME TEXT SE VO NIKAL RHE HAI JSON FORM ME...)

# PARSE_RESUME FUNCTON CALLED...

def parse_resume(resume_text):
    system_prompt = f"""
    You are an expert resume parser.

    Extract information from the resume based on its meaning,
    not only based on exact section headings.

    Different resumes may use different headings.

    For example:
    - Experience
    - Professional Experience
    - Work History
    - Employment
    - Internships

    These may all contain relevant experience.

    Skills may also appear in the skills section, work experience,
    internships or projects.

    Return ONLY valid JSON matching this schema:

    {resume_schema}

    Important rules:

    1. Do not invent information.
    2. If a value is not available, return null.
    3. If a list has no information, return an empty list.
    4. Include internships inside experiences.
    5. Extract skills mentioned across the entire resume.
    """
    user_prompt = f"""
    Parse the following resume:

    {resume_text}
    """
    message_system={
        "role" : "system",
        "content" : system_prompt
    }
    message_user={
        "role" : "user",
        "content" : user_prompt
    }
    messages=[message_system, message_user]
    response_format={
        "type": "json_object"
    }
    response=client.chat.completions.create(model=model, messages=messages, response_format=response_format)
    raw_output = response.choices[0].message.content

    # YHA PR BHI HMARE RESUME KA DATA JSON FORM ME AYA HAI USE REDABLE BNAYA HAI PHIRSE....
    data = json.loads(raw_output)
    resume = Resume(**data)
    return resume


# PART-4 (RESUME JO PDF,WORD FORM ME HOGA USE TEXT ME CONVERT KRDENGE)...
from pypdf import PdfReader
from docx import Document
def read_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def read_docx(file_path):
    document = Document(file_path)
    text = ""
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text += paragraph.text + "\n"
    
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text += cell.text + "\n"
    return text



def read_resume(file_path):
    if file_path.suffix.lower() == ".pdf":
        return read_pdf(file_path)
    elif file_path.suffix.lower() == ".docx":
        return read_docx(file_path)
    else:
        return None



# PART-5 FINAL SCORE NIKALNA JOB,RESUME KO MATCH KRKE....
def final_score(job,resume):
    match_schema = MatchResult.model_json_schema()
    prompt = f"""
    You are an HR recruiter.

    Compare the candidate's resume with the job description.

    JOB DESCRIPTION:
    {job.model_dump_json(indent=2)}

    CANDIDATE RESUME:
    {resume.model_dump_json(indent=2)}


    Return JSON matching this schema:

    {match_schema}

    Give me:

    1. Candidate name
    2. Matching skills
    3. Missing important skills
    4. Whether experience requirement is met
    5. Overall match percentage from 0 to 100
    6. A short final verdict

    Keep the response concise and easy to read.
    """
    message={
        "role": "user",
        "content" : prompt
    }
    messages=[message]


    response_format={
        "type": "json_object"
    }
    response = client.chat.completions.create(model=model, messages=messages, response_format=response_format)
    data = json.loads(response.choices[0].message.content)
    return MatchResult(**data)


# lets do it now-> THIS IS OUR MAIN FUNCTION....

# Resume_folder = Path("resumesfolder") 
# all_results=[]
# # JITNE RESUMES HONGE UNKE RESULT IS ARRAY ME AJAENGE...

# # AB EK FOR LOOP CHALEGA HMARE RESUME_FOLDER ME JO EK EK KRKE SARE RESUMES KO READ KREGA-> FILE _PATH KE ANDR RESUMES KA PATH AJAEGA....
# for file_path in Resume_folder.iterdir():
#     #C:\Users\Pratyush\padho_with_pratyush\week1\day5\resumes\abhay resume new - Abhay Singh.pdf

#     # AGR FILE .PNG,JPG ME HOGI TO ISE SKIP KRDO...
#     if file_path.suffix.lower() not in [".pdf", ".docx"]:
#         continue
#     print("\nProcessing:", file_path.name)

#     # CALLING READ_ RESUME FUNCTION... RESUME PURA TEXT ME CONVERT HOGYA... 
#     resume_text = read_resume(file_path)

#     # CALLING PARSED_RESUME FUMCTION..
#     parsed_resume=parse_resume(resume_text) # llm call1

#     # YE HR 5 SEC ME NYI REQ BHEJEGA GPT,LLM KO -> AGR HM YE BREAK NHI LGAYENGE TO ISSE ** DOS ATTACK(DENIAL OF SERVICE) HOJAEGA..->> SUPPOSE HMNE 50000K RESUMES BHEJDIYE EK SATH ISSE GPT KA SERVER CRASH HOJAEGA ....->> AUR ISKI VJE SE JO NORMAL LOG HAI HMJAISE VO GPT KO USE NHI KRPAENGE...
#     time.sleep(5)

#     #CALLING FINAL_SCORE FUNCTION....
#     result = final_score(job, parsed_resume) #llm caLL2
    

#     time.sleep(5)
#     print("Score:", result.score)
#     all_results.append({
#         "name": parsed_resume.name,
#         "score": result.score,
#         "details": result.details
#     })
# all_results.sort(
#     key=lambda candidate: candidate["score"],
#     reverse=True
# )
# top_2 = all_results[:2]
# worst_2 = all_results[-2:]


# print("TOP 2 CANDIDATES")
# for candidate in top_2:

#     print(
#         candidate["name"],
#         "-",
#         candidate["score"],
#         "%"
#     )

#     print(candidate["details"])

# print("LOWEST 2 CANDIDATES")
# for candidate in worst_2:

#     print(
#         candidate["name"],
#         "-",
#         candidate["score"],
#         "%"
#     )
#     print(candidate["details"])