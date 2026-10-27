🏥 ASHA AI — Autonomous Healthcare Coordination System

Uncertainty-Aware AI for Emergency Healthcare Coordination

ASHA AI is an AI-powered healthcare coordination prototype designed to support emergency response through clinical risk assessment, uncertainty detection, data verification, hospital and ambulance matching, and explainable decision-making.

The system aims to help emergency coordinators identify suitable healthcare resources based on patient needs, resource availability, and operational constraints.

«Project Status: Research and Development Prototype
Domain: Artificial Intelligence, Machine Learning, Healthcare, and Emergency Logistics»

---

📌 Table of Contents

- "Overview" (#-overview)
- "Problem Statement" (#-problem-statement)
- "Proposed Solution" (#-proposed-solution)
- "Key Features" (#-key-features)
- "System Architecture" (#-system-architecture)
- "Technology Stack" (#-technology-stack)
- "Machine Learning Model" (#-machine-learning-model)
- "Project Structure" (#-project-structure)
- "Installation and Setup" (#-installation-and-setup)
- "API Endpoints" (#-api-endpoints)
- "Workflow" (#-system-workflow)
- "Research and Evaluation" (#-research-and-evaluation)
- "Future Enhancements" (#-future-enhancements)
- "Limitations and Safety" (#-limitations-and-safety)
- "Disclaimer" (#-disclaimer)
- "License" (#-license)

---

🔍 Overview

During medical emergencies, identifying appropriate hospitals, available ambulances, and essential medical resources can be challenging.

ASHA AI proposes an integrated decision-support system that combines machine learning with healthcare resource coordination.

Unlike a system that simply generates a prediction, ASHA AI is designed to consider uncertainty, flag potentially unreliable information, explain its recommendations, and support emergency resource matching.

The prototype brings together clinical risk assessment and healthcare logistics in a single architecture.

❗ Problem Statement

Emergency healthcare coordination can be affected by several challenges:

- Delays in identifying appropriate hospitals.
- Limited visibility into healthcare resource availability.
- Inconsistent or outdated resource information.
- Difficulty coordinating ambulances and hospitals.
- Uncertainty in AI-generated clinical predictions.
- Lack of transparency in automated recommendations.

These challenges motivate the development of an AI-assisted system that supports evidence-based and explainable emergency coordination.

💡 Proposed Solution

ASHA AI proposes a modular system that integrates clinical risk assessment, data verification, uncertainty handling, and resource matching.

The system is designed to:

1. Accept patient and emergency information.
2. Estimate clinical risk using a machine learning model.
3. Identify uncertainty or missing information.
4. Flag conflicting or potentially outdated resource data.
5. Rank suitable hospitals and ambulances using configurable criteria.
6. Explain the reasons behind its recommendations.
7. Simulate different resource-availability scenarios.

The prototype is intended to support healthcare professionals and emergency coordinators rather than replace their judgment.

---

🚀 Key Features

1. 🧠 Clinical Risk Assessment

Uses a machine learning model to estimate risk from supported patient features.

- Processes structured clinical data.
- Generates a model prediction.
- Supports evaluation using standard classification metrics.
- Provides a foundation for future clinical validation.

Important: The current baseline model is trained using the UCI Heart Disease dataset. Its predictions are not validated for real-world emergency triage.

2. 🤔 Self-Doubt AI Engine

Designed to identify situations in which the system should avoid making an overconfident recommendation.

Potential checks include:

- Low model confidence.
- Missing patient information.
- Conflicting resource records.
- Stale availability information.
- Insufficient evidence to rank resources reliably.

When these conditions occur, the system can flag the case for additional verification or human review.

3. 🔍 Automatic Data Verification

Checks resource information for potential inconsistencies.

Examples include:

- Conflicting hospital bed counts.
- Missing ambulance status.
- Expired resource updates.
- Invalid or incomplete records.

Verification results can help coordinators determine which information requires confirmation.

4. 🚑 Ambulance Matching

Ranks candidate ambulances using configurable criteria, such as:

- Availability status.
- Estimated travel time.
- Distance from the emergency location.
- Required capabilities.

Actual dispatch decisions require confirmation of real-time availability and authorization by the responsible emergency team.

5. 🏥 Hospital Matching

Ranks hospitals according to the patient's stated requirements and available hospital information.

Potential matching criteria include:

- Relevant department or specialty.
- Available beds.
- Emergency care capabilities.
- Required equipment.
- Estimated travel time.
- Data freshness.

A recommendation does not guarantee that a hospital can accept a patient. Availability must be confirmed directly.

6. 📦 Healthcare Resource Monitoring

Supports tracking of healthcare resources, including:

- Hospital beds.
- Oxygen supplies.
- Blood inventory.
- Essential medicines.
- Ventilators.
- Operating theatre availability.

The reliability of this feature depends on the accuracy and freshness of the underlying data.

7. 🔮 What-If Simulator

Allows users to explore hypothetical scenarios, such as:

- A hospital becoming unavailable.
- An ambulance being assigned to another emergency.
- A change in bed availability.
- A shortage of a required medical resource.

The simulator illustrates possible changes in recommendations without performing real-world dispatch or resource allocation.

8. 📝 Explainable Decision Trail

Records the factors contributing to a recommendation.

A decision trail may include:

- Input information used.
- Resource eligibility checks.
- Matching criteria.
- Data verification warnings.
- Uncertainty flags.
- Reasons for ranking one option above another.

This feature is intended to improve transparency and support human review.

---

🏗️ System Architecture

                  EMERGENCY INPUT
                         |
                         v
                 REACT WEB DASHBOARD
                         |
                         v
                  FASTAPI BACKEND
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
        CLINICAL      DATA         RESOURCE
        RISK MODEL    VERIFIER     MONITORING
             |           |           |
             v           v           v
        RISK SCORE   DATA QUALITY   RESOURCE
                     AND FRESHNESS   STATUS
             |           |           |
             +-----------+-----------+
                         |
                         v
                  SELF-DOUBT ENGINE
                         |
                         v
                 RESOURCE MATCHING
                         |
              +----------+----------+
              |                     |
              v                     v
        HOSPITAL MATCHING     AMBULANCE MATCHING
              |                     |
              +----------+----------+
                         |
                         v
                EXPLAINABLE DECISION
                         |
                         v
                 DASHBOARD RESULTS
                         |
                         v
                 HUMAN VERIFICATION

---

🛠️ Technology Stack

Component| Technology
Frontend| React
Programming Language| TypeScript
Backend| Python
API Framework| FastAPI
Machine Learning| Scikit-learn
Data Processing| Pandas, NumPy
Model Persistence| Joblib
Database| PostgreSQL (planned integration, if not yet implemented)
API Documentation| Swagger UI
Version Control| Git and GitHub

---

🤖 Machine Learning Model

The project includes a baseline clinical classification model trained using the UCI Heart Disease dataset.

Dataset

UCI Heart Disease Dataset

The dataset contains structured clinical attributes associated with heart disease classification.

The current model is intended for demonstrating the machine learning pipeline, not for diagnosing patients or predicting general emergency severity.

Baseline Evaluation

The following results were recorded during an earlier model-training run:

Metric| Recorded Result
Accuracy| 86.84%
Precision| 83.78%
Recall| 88.57%
F1-Score| 86.11%
Test ROC-AUC| 0.9282
Mean 5-Fold CV ROC-AUC| 0.8873
Cross-Validation ROC-AUC Standard Deviation| 0.0429

Confusion matrix:

                 Predicted
                 Negative  Positive

Actual Negative      35        6
Actual Positive       4       31

Evaluation note: These are previously recorded experimental results, not independently reproduced or clinically validated results. The confusion matrix contains 76 observations. The test-set size, splitting procedure, preprocessing pipeline, and potential data leakage should be verified before publishing performance claims.

The results should not be interpreted as evidence of clinical readiness.

Planned Model Improvements

- Evaluate calibration and prediction uncertainty.
- Establish reproducible training and testing procedures.
- Assess performance on an appropriate independent dataset.
- Investigate class imbalance and potential data leakage.
- Document model limitations and failure cases.

---

📁 Project Structure

The following is a proposed logical structure. Adapt the filenames to match the actual repository.

ASHA-AI/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── clinical_baseline.joblib
│   │   ├── models/
│   │   ├── services/
│   │   ├── routes/
│   │   └── schemas/
│   │
│   ├── requirements.txt
│   └── train_model.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   │
│   ├── package.json
│   └── index.html
│
├── data/
│   └── README.md
│
├── tests/
│
├── .gitignore
└── README.md

Some components shown above may still need to be implemented. Keep the repository structure synchronized with the actual codebase.

---

⚙️ Installation and Setup

Prerequisites

Install the following tools:

- Python 3.10 or a compatible version.
- Node.js and npm.
- Git.

1. Clone the Repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ASHA-AI

Replace the placeholder with the actual repository URL.

2. Set Up the Backend

Open a terminal in the backend directory:

cd backend

Create a virtual environment:

Windows PowerShell

python -m venv venv
.\venv\Scripts\Activate.ps1

Install dependencies:

pip install fastapi uvicorn pandas numpy scikit-learn joblib

If a "requirements.txt" file exists, use:

pip install -r requirements.txt

3. Start the Backend

From the backend directory, run:

uvicorn app.main:app --reload

Open the API documentation at:

http://127.0.0.1:8000/docs

The backend must expose the expected application module and routes for this command to work.

4. Set Up the Frontend

Open a second terminal:

cd frontend
npm install

Start the development server:

npm run dev

Open the local address printed by Vite, commonly:

http://localhost:5173

5. Connect Frontend and Backend

Configure the frontend API base URL to point to the running FastAPI server.

Example:

http://127.0.0.1:8000

Configure CORS on the backend for the actual frontend development origin.

Note: Installation commands alone do not guarantee that every feature works. Confirm that the required model file, application routes, environment variables, and frontend API integration are present.

---

🔌 API Endpoints

The following endpoints were identified in the ASHA AI prototype design.

Method| Endpoint| Purpose
GET| "/api/health"| Check backend health
GET| "/api/ambulances"| Retrieve ambulance records
GET| "/api/hospitals"| Retrieve hospital records
POST| "/api/verify-case"| Validate emergency case information
POST| "/api/self-doubt"| Assess uncertainty and verification needs
POST| "/api/match-resources"| Rank candidate healthcare resources
POST| "/api/cross-verify"| Check information across available records

These are the intended prototype endpoints; verify their actual implementation and request schemas in FastAPI Swagger documentation.

---

🔄 System Workflow

1. An authorized user enters emergency and patient information.
2. The backend validates the incoming request.
3. The clinical model generates a risk estimate when applicable.
4. The system checks for missing information and potential uncertainty.
5. Resource records are evaluated for consistency and freshness.
6. Candidate hospitals and ambulances are ranked against configurable criteria.
7. The system produces a recommendation with supporting reasons and warnings.
8. A responsible human reviews and verifies the recommendation before any real-world action.

---

📊 Research and Evaluation

The project can be evaluated using the following measurable criteria.

Component| Evaluation Metric
Clinical risk model| Precision, recall, F1-score, ROC-AUC
Prediction calibration| Brier score and calibration analysis
Uncertainty detection| Error-detection rate and coverage-risk analysis
Data verification| Inconsistency detection precision and recall
Hospital matching| Constraint satisfaction and ranking quality
Ambulance matching| Eligibility, travel-time estimates, and ranking quality
System performance| API latency and error rate
Explainability| Completeness and correctness of decision reasons

Proposed Experiments

Experiment 1: Standard Matching vs. Verification-Aware Matching

Compare resource recommendations when all records are assumed valid against recommendations produced after data-quality checks.

Experiment 2: Uncertainty Handling

Introduce controlled missing, conflicting, and low-confidence inputs. Measure how often the system flags cases requiring verification.

Experiment 3: Resource Availability Changes

Simulate hospital and ambulance availability changes. Measure how quickly and correctly recommendations are updated.

Experiment 4: Explainable Recommendations

Check whether every recommendation includes the relevant criteria, data sources, and verification warnings.

All experiments should clearly distinguish simulated results from observations obtained from real operational systems.

---

🔮 Future Enhancements

- Integrate verified real-time hospital resource feeds.
- Add GPS-based ambulance travel-time estimation.
- Implement role-based authentication and audit logging.
- Introduce a persistent PostgreSQL database.
- Develop improved uncertainty estimation and model calibration.
- Add multilingual support, including Tamil and English.
- Build a simulation environment for emergency surge scenarios.
- Conduct external validation with qualified healthcare partners.
- Evaluate privacy, security, fairness, and failure recovery.

---

⚠️ Limitations and Safety

- The prototype does not replace doctors, emergency dispatchers, or hospital coordinators.
- The baseline heart disease model is not a validated emergency triage model.
- Resource recommendations are only as reliable as the underlying data.
- Simulated or manually entered resource records must not be presented as live hospital information.
- Real-time hospital and ambulance availability requires verified integrations.
- Clinical and operational deployment requires appropriate validation, security controls, and authorization.
- Human review is required before consequential medical or emergency resource decisions.

---

📌 Disclaimer

ASHA AI is an academic and research-oriented prototype for exploring AI-assisted healthcare coordination.

It is not a certified medical device, an emergency dispatch service, or a substitute for professional medical advice.

Predictions and recommendations must not be used as the sole basis for diagnosis, treatment, ambulance dispatch, or hospital admission decisions.

For an actual medical emergency, contact the appropriate local emergency service.

---

👨‍💻 Project Vision

ASHA AI aims to make emergency healthcare coordination more transparent, uncertainty-aware, and resource-efficient through explainable artificial intelligence.

The long-term research goal is to investigate how clinical risk assessment, information verification, and resource-matching systems can work together to support responsible emergency decision-making.

---

Developed for: Academic Research and Healthcare AI Innovation

Project Name: ASHA AI

Focus Areas: AI/ML, Healthcare Coordination, Emergency Logistics, Explainable AI, and Uncertainty-Aware Decision Support
