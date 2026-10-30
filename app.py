import streamlit as st
import resumeparser
import database

import tempfile
import os
from pathlib import Path

# -----------------------------
# PAGE CONFIGURATION
# -----------------------------

st.set_page_config(
    page_title="AI Resume Parser",
    page_icon="🤖",
    layout="wide"
)

st.success("resumeparser.py connected successfully!")

# -----------------------------
# TITLE
# -----------------------------

st.title("🤖 AI Resume Screening System")

st.write(
    "Analyze resumes using AI and compare candidates "
    "with a given job description."
)

st.divider()

# -----------------------------
# JOB DESCRIPTION
# -----------------------------

st.subheader("📋 Job Description")

job_description = st.text_area(
    "Paste the job description below:",
    height=250,
    placeholder="Paste the complete job description here..."
)

# -----------------------------
# RESUME UPLOAD
# -----------------------------

st.subheader("📄 Upload Resumes")

uploaded_files = st.file_uploader(
    "Upload PDF or DOCX resumes",
    type=["pdf", "docx"],
    accept_multiple_files=True
)


# -----------------------------------
# NUMBER OF CANDIDATES TO SHORTLIST
# -----------------------------------

if uploaded_files:

    top_n = st.selectbox(
        "🏆 Number of candidates to shortlist",
        options=list(range(1, len(uploaded_files) + 1)),
        index=min(1, len(uploaded_files) - 1)
    )
    

# -----------------------------
# ANALYZE BUTTON
# -----------------------------

if st.button("🚀 Analyze Resumes", type="primary"):

    if not job_description:
        st.warning("Please enter a job description.")

    elif not uploaded_files:
        st.warning("Please upload at least one resume.")

    else:

        # -----------------------------------
        # STEP 1: ANALYZE JOB DESCRIPTION
        # -----------------------------------

        with st.spinner("🤖 Analyzing job description..."):

            job = resumeparser.parse_job_description(
                job_description
            )

        st.success(
            "✅ Job description analyzed successfully!"
        )

        # -----------------------------------
        # STEP 2: SHOW JOB INFORMATION
        # -----------------------------------

        st.subheader("📋 Extracted Job Information")

        st.write(
            "**Role:**",
            job.role
        )

        st.write(
            "**Required Skills:**",
            ", ".join(job.required_skills)
        )

        st.write(
            "**Preferred Skills:**",
            ", ".join(job.preferred_skills)
        )

        st.write(
            "**Minimum Experience:**",
            job.minimum_experience
        )

        st.divider()

        # -----------------------------------
        # STEP 3: PROCESS ALL RESUMES
        # -----------------------------------

        st.subheader("📄 Processing Resumes")

        results = []

        progress_bar = st.progress(0)

        total_resumes = len(uploaded_files)

        for index, uploaded_file in enumerate(
            uploaded_files
        ):

            # Get file extension
            suffix = Path(
                uploaded_file.name
            ).suffix.lower()

            # Create temporary file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as temp_file:

                temp_file.write(
                    uploaded_file.getbuffer()
                )

                temp_path = Path(
                    temp_file.name
                )

            try:

                # -----------------------------
                # READ RESUME
                # -----------------------------

                with st.spinner(
                    f"📖 Reading {uploaded_file.name}..."
                ):

                    resume_text = (
                        resumeparser.read_resume(
                            temp_path
                        )
                    )

                if not resume_text:

                    st.warning(
                        f"⚠️ Could not extract text from "
                        f"{uploaded_file.name}"
                    )

                    continue

                # -----------------------------
                # PARSE RESUME
                # -----------------------------

                with st.spinner(
                    f"🤖 Analyzing {uploaded_file.name}..."
                ):

                    parsed_resume = (
                        resumeparser.parse_resume(
                            resume_text
                        )
                    )

                # -----------------------------
                # CALCULATE MATCH SCORE
                # -----------------------------

                with st.spinner(
                    "📊 Calculating match score..."
                ):

                    result = (
                        resumeparser.final_score(
                            job,
                            parsed_resume
                        )
                    )

                # -----------------------------
                # STORE RESULT
                # -----------------------------


                results.append({
                    "name": parsed_resume.name,
                    "email": parsed_resume.email,
                    "skills": parsed_resume.skills,
                    "score": result.score,
                    "details": result.details
                })

                # ============================================================
                # 💾 SAVE TO AIVEN CLOUD DATABASE (ADD THIS BLOCK)
                # ============================================================
                try:
                    # 1. Establish a live cloud connection
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    
                    # 2. Write the SQL insert query matching your database.py script
                    insert_query = """
                        INSERT INTO resume_results (candidate_name, candidate_email, match_score) 
                        VALUES (%s, %s, %s)
                    """
                    
                    # 3. Pull values directly from your parsed_resume object
                    # Uses fallbacks in case a candidate forgot their name/email on their resume
                    db_name = parsed_resume.name if parsed_resume.name else uploaded_file.name
                    db_email = parsed_resume.email if parsed_resume.email else "No Email Found"
                    db_score = int(result.score)
                    
                    # 4. Push data to the cloud service and save it
                    cursor.execute(insert_query, (db_name, db_email, db_score))
                    conn.commit()
                    
                    # 5. Clean up connection points and toast the user dashboard
                    cursor.close()
                    conn.close()
                    st.toast(f"💾 Saved {db_name}'s results to Aiven Cloud!")
                    
                except Exception as db_err:
                    st.error(f"Database Storage Error: {db_err}")
                # ============================================================

            except Exception as e:


                st.error(
                    f"❌ Error processing "
                    f"{uploaded_file.name}: {e}"
                )

            finally:

                # Delete temporary file
                if temp_path.exists():
                    os.remove(temp_path)

            # Update progress
            progress_bar.progress(
                (index + 1) / total_resumes
            )

        # -----------------------------------
        # STEP 4: RANK CANDIDATES
        # -----------------------------------

        if results:

            # Sort candidates by score
            results.sort(
                key=lambda x: x["score"],
                reverse=True
            )

            # Select requested number
            top_candidates = results[:top_n]

            st.divider()

            st.header(
                f"🏆 Top {len(top_candidates)} "
                f"Candidates"
            )

            st.write(
                f"Analyzed **{len(results)}** "
                f"successful resumes."
            )

            # -----------------------------------
            # STEP 5: DISPLAY TOP CANDIDATES
            # -----------------------------------

            for rank, candidate in enumerate(
                top_candidates,
                start=1
            ):

                st.subheader(
                    f"#{rank} — {candidate['name']}"
                )

                # Candidate basic information
                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "**Email:**",
                        candidate["email"]
                    )

                with col2:

                    st.metric(
                        "Match Score",
                        f"{candidate['score']}%"
                    )

                details = candidate["details"]

                # -----------------------------------
                # MATCH STATUS
                # -----------------------------------

                score = details.get(
                    "overall_match_percentage",
                    candidate["score"]
                )

                if score >= 80:

                    status = "🟢 Excellent Match"

                elif score >= 60:

                    status = "🟡 Good Match"

                else:

                    status = "🔴 Low Match"

                st.write(
                    f"### {status}"
                )

                # -----------------------------------
                # SKILLS
                # -----------------------------------

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        "#### ✅ Matching Skills"
                    )

                    matching_skills = details.get(
                        "matching_skills",
                        []
                    )

                    if matching_skills:

                        for skill in matching_skills:

                            st.success(
                                f"✓ {skill}"
                            )

                    else:

                        st.info(
                            "No matching skills found."
                        )

                with col2:

                    st.write(
                        "#### ❌ Missing Important Skills"
                    )

                    missing_skills = details.get(
                        "missing_important_skills",
                        []
                    )

                    if missing_skills:

                        for skill in missing_skills:

                            st.error(
                                f"✗ {skill}"
                            )

                    else:

                        st.success(
                            "No important skills missing!"
                        )

                # -----------------------------------
                # REQUIREMENT CHECK
                # -----------------------------------

                st.write(
                    "### 🎓 Requirement Check"
                )

                col1, col2 = st.columns(2)

                with col1:

                    if details.get(
                        "experience_requirement_met"
                    ):

                        st.success(
                            "✅ Experience requirement met"
                        )

                    else:

                        st.error(
                            "❌ Experience requirement "
                            "not met"
                        )

                with col2:

                    if details.get(
                        "education_requirement_met"
                    ):

                        st.success(
                            "✅ Education requirement met"
                        )

                    else:

                        st.error(
                            "❌ Education requirement "
                            "not met"
                        )

                # -----------------------------------
                # AI VERDICT
                # -----------------------------------

                st.write(
                    "### 🤖 AI Verdict"
                )

                st.info(
                    details.get(
                        "verdict",
                        "No verdict available."
                    )
                )

                st.divider()

        else:

            st.error(
                "❌ No resumes could be successfully analyzed."
            )