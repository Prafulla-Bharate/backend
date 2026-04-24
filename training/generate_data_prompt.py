"""
generate_data_prompt.py
-----------------------
Prints a structured LLM prompt for generating career training data.

Usage:
    python generate_data_prompt.py                          # Full prompt (all 30 careers)
    python generate_data_prompt.py --career "Data Scientist"  # Prompt for one career
    python generate_data_prompt.py --list                   # List all 30 career classes
    python generate_data_prompt.py --schema                 # Print JSON schema only
    python generate_data_prompt.py --count 70               # Override samples per career

Output the printed prompt into any LLM (ChatGPT-4o, Claude, Gemini) and save the
JSON response as:
    training/data/batch_001.json         (first run, 30 careers × 70 = 2100 profiles)
    training/data/batch_002.json         (second run for more data)
    ...

The training script (train_career_model.py) merges all batch_*.json files automatically.
"""

import argparse
import json
import sys

# ─────────────────────────────────────────────────────────────────────────────
# 30 INDIA-FOCUSED CAREER CLASSES — with representative skill pools
# (training script uses these as the allowed label space)
# ─────────────────────────────────────────────────────────────────────────────
CAREER_PROFILES = {
    "Backend Developer": {
        "core_skills": ["Python", "Django", "Flask", "FastAPI", "Node.js", "Express.js",
                        "PostgreSQL", "MySQL", "MongoDB", "Redis", "REST API", "GraphQL",
                        "Docker", "Git", "Linux", "Celery", "RabbitMQ", "JWT",
                        "OAuth2", "Unit Testing", "SQLAlchemy", "Nginx"],
        "distinguishing": "PRIMARY focus is server-side APIs and databases. NO frontend HTML/CSS skills. Does NOT own CI/CD pipelines (that's DevOps). Distinguish from Python Developer by being polyglot (Python + Node.js both acceptable).",
        "fresher_skills": ["Python", "Django", "MySQL", "REST API", "Git"],
        "senior_skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Redis", "Docker",
                          "RabbitMQ", "Celery", "GraphQL", "Nginx", "JWT", "Linux", "Git"],
        "job_titles": ["Software Developer", "Backend Developer", "Junior Software Developer",
                       "Software Engineer", "Associate Developer", "API Developer",
                       "Software Trainee", "Junior Backend Engineer"],
        "industries": ["IT Services", "Product Startup", "E-commerce", "Fintech",
                       "Healthtech", "Edtech", "SaaS"],
        "degrees": ["bachelor", "btech", "master", "mca"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["AWS Developer Associate", "Oracle Java SE", "MongoDB Certified Developer",
                  "Docker Certified Associate", "Python Institute PCEP"],
    },
    "Frontend Developer": {
        "core_skills": ["JavaScript", "TypeScript", "React", "Vue.js", "Angular",
                        "HTML", "CSS", "Tailwind CSS", "Bootstrap", "Redux",
                        "Webpack", "Vite", "REST API", "Git", "Figma",
                        "Jest", "Next.js", "SASS", "Storybook", "Responsive Design"],
        "distinguishing": "PRIMARY focus is browser UI. Must have HTML+CSS+JS as core. NO server-side database skills. Distinguish from Full Stack by having NO backend framework (no Django/Node server-side).",
        "fresher_skills": ["HTML", "CSS", "JavaScript", "React", "Git"],
        "senior_skills": ["TypeScript", "React", "Next.js", "Redux", "Tailwind CSS",
                          "Webpack", "Jest", "REST API", "Figma", "CI/CD", "Git"],
        "job_titles": ["Frontend Developer", "UI Developer", "Web Developer",
                       "Software Developer", "Junior Frontend Engineer",
                       "UI/Frontend Trainee", "React Developer", "Angular Developer"],
        "industries": ["IT Services", "Product Startup", "E-commerce",
                       "Advertising Tech", "Edtech", "SaaS"],
        "degrees": ["bachelor", "btech", "diploma", "master"],
        "fields": ["Computer Science", "Information Technology", "Multimedia"],
        "certs": ["Meta Frontend Developer Certificate", "Google UX Design",
                  "AWS Cloud Practitioner", "freeCodeCamp Responsive Web Design"],
    },
    "Full Stack Developer": {
        "core_skills": ["JavaScript", "TypeScript", "React", "Node.js", "Express.js",
                        "Python", "Django", "PostgreSQL", "MongoDB", "Docker",
                        "Git", "REST API", "Redis", "Nginx", "CI/CD",
                        "HTML", "CSS", "JWT", "GraphQL", "Linux"],
        "distinguishing": "Must have BOTH frontend (React/Angular/Vue + HTML/CSS) AND backend (Node.js or Django or Spring Boot) skills. Distinguish from Backend Developer by having frontend skills. Distinguish from Frontend by having server-side skills.",
        "fresher_skills": ["HTML", "CSS", "JavaScript", "React", "Node.js", "MongoDB", "Git"],
        "senior_skills": ["TypeScript", "React", "Node.js", "PostgreSQL", "Docker",
                          "Redis", "GraphQL", "CI/CD", "Nginx", "Python", "Git", "JWT"],
        "job_titles": ["Full Stack Developer", "Software Developer", "Web Developer",
                       "Senior Developer", "MEAN Stack Developer", "MERN Stack Developer",
                       "Software Engineer", "Full Stack Engineer"],
        "industries": ["IT Services", "Product Startup", "Consulting", "E-commerce",
                       "Fintech", "Edtech"],
        "degrees": ["bachelor", "btech", "master", "diploma"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["AWS Developer Associate", "MongoDB Certified Developer",
                  "Meta Full Stack Developer"],
    },
    "Data Scientist": {
        "core_skills": ["Python", "Machine Learning", "Deep Learning", "Pandas", "NumPy",
                        "Scikit-learn", "TensorFlow", "PyTorch", "SQL", "Statistics",
                        "Data Visualization", "Matplotlib", "Seaborn", "Jupyter",
                        "Feature Engineering", "NLP", "XGBoost", "A/B Testing",
                        "Hypothesis Testing", "R", "Regression", "Classification"],
        "distinguishing": "Focus is on STATISTICAL ANALYSIS, building and evaluating predictive models, and presenting insights. Has strong statistics background. Distinguish from ML Engineer by having less MLOps/deployment and more analytical/business insight skills. Distinguish from Data Analyst by having ML model-building skills.",
        "fresher_skills": ["Python", "Pandas", "NumPy", "Scikit-learn", "SQL",
                           "Statistics", "Matplotlib", "Jupyter"],
        "senior_skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "XGBoost",
                          "NLP", "Deep Learning", "SQL", "A/B Testing", "Feature Engineering",
                          "Pandas", "Statistics", "Seaborn", "Jupyter"],
        "job_titles": ["Data Scientist", "Junior Data Scientist", "Research Analyst",
                       "ML Analyst", "Business Intelligence Analyst", "Data Science Intern",
                       "Associate Data Scientist", "Analytics Engineer"],
        "industries": ["IT Services", "Analytics", "Fintech", "Healthcare",
                       "E-commerce", "Edtech", "BFSI", "Pharma"],
        "degrees": ["master", "bachelor", "phd", "btech"],
        "fields": ["Computer Science", "Statistics", "Mathematics", "Data Science",
                   "Physics", "Economics"],
        "certs": ["Google Data Analytics Professional", "IBM Data Science Professional",
                  "Coursera ML Specialization (Andrew Ng)", "AWS Certified Machine Learning",
                  "DataCamp Data Scientist Track"],
    },
    "ML Engineer": {
        "core_skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "MLflow",
                        "Docker", "Kubernetes", "AWS SageMaker", "Feature Stores",
                        "Model Deployment", "REST API", "FastAPI", "Git", "SQL",
                        "Spark", "Airflow", "LLM Fine-tuning", "Hugging Face",
                        "ONNX", "Model Monitoring", "CI/CD for ML"],
        "distinguishing": "Focus is PRODUCTIONIZING ML models — pipelines, deployment, monitoring, MLOps. Has strong software engineering skills alongside ML. Distinguish from Data Scientist by having Docker/Kubernetes/deployment skills. Distinguish from AI Research Engineer by being application-focused (not academic papers).",
        "fresher_skills": ["Python", "Scikit-learn", "TensorFlow", "Pandas",
                           "Docker", "REST API", "Git", "SQL"],
        "senior_skills": ["Python", "PyTorch", "TensorFlow", "MLflow", "Docker",
                          "Kubernetes", "AWS SageMaker", "Airflow", "FastAPI",
                          "LLM Fine-tuning", "Hugging Face", "CI/CD for ML", "Feature Stores"],
        "job_titles": ["ML Engineer", "MLOps Engineer", "AI Engineer",
                       "Applied Scientist", "Junior ML Engineer",
                       "Machine Learning Developer", "AI Developer"],
        "industries": ["AI Startup", "Product Startup", "Research Lab", "Fintech",
                       "E-commerce", "Healthcare AI", "Automotive AI"],
        "degrees": ["master", "bachelor", "phd", "btech"],
        "fields": ["Computer Science", "Mathematics", "Statistics",
                   "Artificial Intelligence", "Data Science"],
        "certs": ["AWS Certified ML Specialty", "Google Professional ML Engineer",
                  "Deep Learning Specialization", "MLflow Certified"],
    },
    "Data Engineer": {
        "core_skills": ["Python", "Apache Spark", "Apache Kafka", "Airflow",
                        "SQL", "AWS", "GCP", "BigQuery", "Snowflake", "dbt",
                        "ETL", "Hadoop", "Hive", "PostgreSQL", "Docker", "Git",
                        "Data Warehousing", "Delta Lake", "Redshift", "Data Modeling",
                        "Scala", "PySpark", "Azure Data Factory"],
        "distinguishing": "Focus is BUILDING DATA PIPELINES and infrastructure (ETL, warehouses, Kafka, Spark). Does NOT build ML models. Distinguish from Data Scientist by having no ML model training. Distinguish from Data Analyst by building pipelines, not reporting.",
        "fresher_skills": ["Python", "SQL", "ETL", "Apache Spark", "Git", "Airflow"],
        "senior_skills": ["Python", "Apache Spark", "Apache Kafka", "Airflow", "dbt",
                          "Snowflake", "BigQuery", "Delta Lake", "AWS", "Docker",
                          "Data Warehousing", "PySpark", "Data Modeling"],
        "job_titles": ["Data Engineer", "ETL Developer", "Data Pipeline Engineer",
                       "BI Developer", "Big Data Engineer", "Junior Data Engineer",
                       "Analytics Engineer", "Data Infrastructure Engineer"],
        "industries": ["Analytics", "IT Services", "E-commerce", "Fintech",
                       "Telecom", "Retail", "Healthcare"],
        "degrees": ["bachelor", "btech", "master", "mca"],
        "fields": ["Computer Science", "Information Technology", "Data Science",
                   "Mathematics"],
        "certs": ["AWS Data Analytics Specialty", "Google Professional Data Engineer",
                  "Databricks Certified Associate Developer for Apache Spark",
                  "Snowflake SnowPro Core"],
    },
    "Data Analyst": {
        "core_skills": ["SQL", "Python", "Excel", "Power BI", "Tableau",
                        "Data Visualization", "Statistics", "Pandas", "Google Data Studio",
                        "A/B Testing", "Business Analysis", "DAX", "Looker",
                        "VLOOKUP", "PivotTables", "Reporting", "Dashboard Design",
                        "Google Analytics", "Cohort Analysis"],
        "distinguishing": "Focus is REPORTING and INSIGHTS from existing data, NOT building models. Uses SQL and BI tools heavily. Distinguish from Data Scientist by having no machine learning skills. Has strong Excel and BI tool proficiency.",
        "fresher_skills": ["SQL", "Excel", "Power BI", "Data Visualization",
                           "Statistics", "Pandas"],
        "senior_skills": ["SQL", "Python", "Tableau", "Power BI", "DAX",
                          "A/B Testing", "Statistics", "Pandas", "Google Data Studio",
                          "Looker", "Business Analysis", "Dashboard Design"],
        "job_titles": ["Data Analyst", "Business Analyst", "MIS Analyst",
                       "Reporting Analyst", "Operations Analyst", "Data Analyst Intern",
                       "Junior Analyst", "Analytics Associate"],
        "industries": ["Analytics", "IT Services", "E-commerce", "BFSI",
                       "Consulting", "Healthcare", "Retail", "Media"],
        "degrees": ["bachelor", "btech", "master", "mca", "diploma"],
        "fields": ["Computer Science", "Statistics", "Commerce", "Mathematics",
                   "Economics", "Business Administration"],
        "certs": ["Google Data Analytics Professional", "Microsoft Power BI Data Analyst",
                  "Tableau Desktop Specialist", "SQL for Data Science (Coursera)"],
    },
    "DevOps Engineer": {
        "core_skills": ["Linux", "Docker", "Kubernetes", "Terraform", "Jenkins",
                        "GitHub Actions", "CI/CD", "AWS", "GCP", "Azure",
                        "Ansible", "Helm", "Prometheus", "Grafana", "Nginx",
                        "Shell Scripting", "Python", "Git", "ELK Stack",
                        "SRE Practices", "Incident Management", "ArgoCD"],
        "distinguishing": "PRIMARY focus is AUTOMATING deployments and managing infrastructure. Owns CI/CD pipelines. Distinguish from Cloud Engineer by being pipeline/automation focused, not pure cloud provisioning. Distinguish from Systems Admin by using containers/IaC.",
        "fresher_skills": ["Linux", "Docker", "Git", "Shell Scripting", "Jenkins", "AWS"],
        "senior_skills": ["Kubernetes", "Terraform", "Ansible", "Helm", "Prometheus",
                          "Grafana", "CI/CD", "ArgoCD", "ELK Stack", "AWS", "Docker", "Linux"],
        "job_titles": ["DevOps Engineer", "Junior DevOps Engineer", "Build Engineer",
                       "Infrastructure Engineer", "Site Reliability Engineer",
                       "Platform Engineer", "DevOps Trainee"],
        "industries": ["IT Services", "Product Startup", "Fintech", "E-commerce",
                       "SaaS", "Gaming"],
        "degrees": ["bachelor", "btech", "diploma", "master"],
        "fields": ["Computer Science", "Information Technology", "Networking",
                   "Software Engineering"],
        "certs": ["CKA (Certified Kubernetes Administrator)", "AWS Solutions Architect Associate",
                  "Terraform Associate", "Google Professional DevOps Engineer",
                  "Red Hat Certified Engineer (RHCE)"],
    },
    "Cloud Engineer": {
        "core_skills": ["AWS", "GCP", "Azure", "Terraform", "Kubernetes",
                        "Docker", "Networking", "IAM", "S3", "EC2", "Lambda",
                        "VPC", "CloudFormation", "CDN", "Linux", "Python",
                        "Cloud Security", "Cost Optimization", "EKS", "GKE",
                        "Azure Blob Storage", "CloudWatch", "Auto Scaling"],
        "distinguishing": "PRIMARY focus is CLOUD INFRASTRUCTURE — provisioning, cloud services, networking, IAM. Distinguish from DevOps by not owning CI/CD pipelines. Distinguishes from Systems Admin by working exclusively on cloud (no on-premise). Cloud certifications are a strong signal.",
        "fresher_skills": ["AWS", "Linux", "Networking", "IAM", "EC2", "S3", "Python"],
        "senior_skills": ["AWS", "GCP", "Azure", "Terraform", "Kubernetes", "EKS",
                          "VPC", "CloudFormation", "IAM", "Lambda", "Docker",
                          "Cloud Security", "Cost Optimization", "CDN"],
        "job_titles": ["Cloud Engineer", "Cloud Infrastructure Engineer",
                       "AWS Engineer", "Cloud Architect", "Junior Cloud Engineer",
                       "Infrastructure Engineer", "Cloud Associate"],
        "industries": ["IT Services", "Consulting", "Product Startup", "Fintech",
                       "Healthcare", "E-commerce"],
        "degrees": ["bachelor", "btech", "master", "diploma"],
        "fields": ["Computer Science", "Information Technology", "Networking",
                   "Electrical Engineering"],
        "certs": ["AWS Solutions Architect Associate", "Google Associate Cloud Engineer",
                  "Microsoft Azure Administrator (AZ-104)", "AWS Cloud Practitioner",
                  "AWS DevOps Engineer Professional"],
    },
    "Android Developer": {
        "core_skills": ["Kotlin", "Java", "Android SDK", "Jetpack Compose",
                        "Room Database", "Retrofit", "MVVM", "Coroutines", "Hilt",
                        "Firebase", "REST API", "Git", "Gradle", "Material Design",
                        "WorkManager", "Navigation Component", "LiveData", "Flow",
                        "Google Play Store", "Push Notifications"],
        "distinguishing": "EXCLUSIVELY Android mobile. Must have Kotlin or Java + Android SDK. NO iOS Swift skills. NO web frontend HTML/CSS. Distinguish from iOS Developer by platform.",
        "fresher_skills": ["Kotlin", "Android SDK", "XML Layouts", "REST API",
                           "Git", "Firebase"],
        "senior_skills": ["Kotlin", "Jetpack Compose", "MVVM", "Hilt",
                          "Room Database", "Coroutines", "Retrofit", "Firebase",
                          "Material Design", "Navigation Component", "WorkManager"],
        "job_titles": ["Android Developer", "Mobile Developer", "Android Engineer",
                       "Junior Android Developer", "App Developer",
                       "Android Trainee", "Software Developer"],
        "industries": ["Product Startup", "IT Services", "E-commerce", "Edtech",
                       "Fintech", "Healthtech"],
        "degrees": ["bachelor", "btech", "diploma", "master"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["Google Associate Android Developer", "Kotlin Certification",
                  "Jetpack Compose Certification"],
    },
    "iOS Developer": {
        "core_skills": ["Swift", "SwiftUI", "UIKit", "Xcode", "Core Data",
                        "Combine", "CocoaPods", "Swift Package Manager",
                        "REST API", "Firebase", "Git", "MVVM", "ARKit",
                        "MapKit", "App Store Connect", "Push Notifications",
                        "CoreBluetooth", "CoreML", "TestFlight"],
        "distinguishing": "EXCLUSIVELY iOS/macOS. Must have Swift + Xcode. NO Android Kotlin skills. NO web frontend. Distinguish from Android Developer by platform.",
        "fresher_skills": ["Swift", "UIKit", "Xcode", "REST API", "Git", "Firebase"],
        "senior_skills": ["Swift", "SwiftUI", "UIKit", "Combine", "Core Data",
                          "ARKit", "CoreML", "Firebase", "Xcode",
                          "App Store Connect", "TestFlight", "MVVM"],
        "job_titles": ["iOS Developer", "Mobile Developer", "iOS Engineer",
                       "Software Developer", "App Developer",
                       "Senior iOS Developer", "Junior iOS Developer"],
        "industries": ["Product Startup", "IT Services", "Fintech", "Healthtech",
                       "E-commerce", "Media"],
        "degrees": ["bachelor", "btech", "master", "diploma"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["Apple Certified Developer", "AWS Cloud Practitioner",
                  "Udemy iOS Development Bootcamp"],
    },
    "QA Engineer": {
        "core_skills": ["Selenium", "Cypress", "TestNG", "JUnit", "Postman",
                        "API Testing", "Manual Testing", "JIRA", "SQL",
                        "Python", "Java", "Performance Testing", "JMeter",
                        "BDD", "Cucumber", "Git", "CI/CD",
                        "Test Plans", "Test Cases", "Bug Reporting",
                        "Regression Testing", "Appium", "Playwright"],
        "distinguishing": "Focus is QUALITY ASSURANCE and testing. Has both manual and automation testing skills. Distinguish from Software Developer by not writing production code. Strong Selenium/Cypress/Postman skills are the primary signal.",
        "fresher_skills": ["Manual Testing", "JIRA", "SQL", "Test Cases",
                           "Bug Reporting", "Postman"],
        "senior_skills": ["Selenium", "Cypress", "TestNG", "JMeter",
                          "API Testing", "Python", "BDD", "Cucumber",
                          "CI/CD", "Performance Testing", "Playwright", "Appium"],
        "job_titles": ["QA Analyst", "QA Engineer", "Test Engineer",
                       "Manual Tester", "SDET", "Quality Analyst",
                       "QA Trainee", "Automation Test Engineer"],
        "industries": ["IT Services", "Product Startup", "Consulting", "BFSI",
                       "Healthcare", "E-commerce"],
        "degrees": ["bachelor", "btech", "diploma", "mca", "master"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["ISTQB Foundation Level", "Selenium WebDriver Certification",
                  "AWS Cloud Practitioner", "Postman API Fundamentals"],
    },
    "Business Analyst": {
        "core_skills": ["Requirements Gathering", "Business Process Modeling",
                        "SQL", "Excel", "Power BI", "JIRA", "Confluence",
                        "Stakeholder Management", "Use Cases", "UML",
                        "Agile", "Scrum", "Data Analysis", "Tableau",
                        "Functional Specifications", "Gap Analysis",
                        "BPMN", "Wireframing", "User Stories"],
        "distinguishing": "Bridge between business and IT. Focus is REQUIREMENTS ANALYSIS, process documentation, and stakeholder communication. Does NOT build products (that's PM) or write code. Distinguish from Data Analyst by having process modeling and requirements skills.",
        "fresher_skills": ["Requirements Gathering", "Excel", "SQL",
                           "User Stories", "JIRA", "Agile"],
        "senior_skills": ["Requirements Gathering", "BPMN", "UML", "SQL",
                          "Power BI", "JIRA", "Stakeholder Management",
                          "Agile", "Scrum", "Data Analysis", "Tableau", "Confluence"],
        "job_titles": ["Business Analyst", "Systems Analyst", "Jr. Business Analyst",
                       "Operations Analyst", "IT Business Analyst",
                       "Business Analyst Trainee", "Process Analyst"],
        "industries": ["IT Services", "Consulting", "BFSI", "E-commerce",
                       "Healthcare", "Government", "Manufacturing"],
        "degrees": ["bachelor", "master", "mba", "btech"],
        "fields": ["Business Administration", "Computer Science", "Commerce",
                   "Management", "Information Technology"],
        "certs": ["CBAP (Certified Business Analysis Professional)", "PMI-PBA",
                  "Agile BA Certification", "IIBA Entry Certificate (ECBA)"],
    },
    "Product Manager": {
        "core_skills": ["Product Roadmap", "User Research", "Agile", "Scrum",
                        "SQL", "A/B Testing", "Jira", "Figma", "Data Analysis",
                        "Stakeholder Management", "OKRs", "GTM Strategy",
                        "Customer Development", "Competitor Analysis",
                        "Product Metrics", "Prioritization Frameworks",
                        "Wireframing", "PRD Writing", "MoSCoW method"],
        "distinguishing": "Owns the PRODUCT VISION and roadmap. Balances business, user, and tech needs. Does NOT write code. Distinguish from Business Analyst by being strategy/roadmap focused (not requirements documentation). Senior PMs have 5+ years; APMs are freshers from MBA/engineering.",
        "fresher_skills": ["Jira", "User Research", "Agile", "Product Roadmap",
                           "Figma", "Stakeholder Management"],
        "senior_skills": ["Product Roadmap", "OKRs", "A/B Testing", "SQL",
                          "Data Analysis", "Figma", "GTM Strategy",
                          "Stakeholder Management", "Competitor Analysis",
                          "PRD Writing", "Scrum", "Customer Development"],
        "job_titles": ["Associate Product Manager", "Product Manager",
                       "Junior Product Manager", "Product Analyst",
                       "APM (Associate PM)", "Senior Product Manager",
                       "Group Product Manager"],
        "industries": ["Product Startup", "E-commerce", "Fintech", "SaaS",
                       "Edtech", "Healthtech", "Gaming"],
        "degrees": ["bachelor", "master", "mba", "btech"],
        "fields": ["Business Administration", "Computer Science", "Management",
                   "Engineering", "Economics"],
        "certs": ["Product School PM Certification", "Google Analytics",
                  "Scrum Master (CSM)", "AIPMM Certified Product Manager"],
    },
    "UI/UX Designer": {
        "core_skills": ["Figma", "Adobe XD", "Sketch", "Prototyping", "Wireframing",
                        "User Research", "Usability Testing", "Design Systems",
                        "HTML", "CSS", "Accessibility", "Information Architecture",
                        "Interaction Design", "Visual Design", "User Journey Mapping",
                        "InVision", "Zeplin", "Motion Design", "Color Theory",
                        "Typography"],
        "distinguishing": "PRIMARY focus is USER EXPERIENCE and visual design. Uses Figma/Adobe XD. Distinguish from Frontend Developer by having no JavaScript/React skills (Figma is the tool, not code). Distinguish from Product Manager by being design-execution focused.",
        "fresher_skills": ["Figma", "Wireframing", "Prototyping",
                           "User Research", "Visual Design"],
        "senior_skills": ["Figma", "Adobe XD", "Design Systems", "Prototyping",
                          "User Research", "Usability Testing", "Accessibility",
                          "Information Architecture", "User Journey Mapping",
                          "Interaction Design", "Zeplin"],
        "job_titles": ["UI Designer", "UX Designer", "Product Designer",
                       "Visual Designer", "Interaction Designer",
                       "UI/UX Intern", "UX Researcher", "Design Lead"],
        "industries": ["Product Startup", "IT Services", "E-commerce",
                       "Advertising Tech", "Edtech", "Media", "Gaming"],
        "degrees": ["bachelor", "diploma", "master"],
        "fields": ["Design", "Computer Science", "Fine Arts", "Multimedia",
                   "Human-Computer Interaction", "Communication Design"],
        "certs": ["Google UX Design Certificate", "Interaction Design Foundation",
                  "Adobe Certified Professional", "Nielsen Norman Group UX Certification"],
    },
    "Cybersecurity Engineer": {
        "core_skills": ["Network Security", "Penetration Testing", "SIEM",
                        "Vulnerability Assessment", "Firewalls", "IDS/IPS",
                        "Linux", "Python", "OWASP", "Ethical Hacking",
                        "Incident Response", "SOC", "Kali Linux", "Wireshark",
                        "Metasploit", "Burp Suite", "VAPT", "NIST Framework",
                        "Threat Modeling", "DLP", "OSINT"],
        "distinguishing": "Focus is SECURITY — vulnerability assessment, penetration testing, SOC operations. Has Kali Linux, Burp Suite, Metasploit skills. Distinguish from Network Engineer by having offensive/defensive security focus, not routing/switching.",
        "fresher_skills": ["Linux", "Network Security", "Wireshark",
                           "OWASP", "Python", "Kali Linux"],
        "senior_skills": ["Penetration Testing", "SIEM", "Vulnerability Assessment",
                          "Metasploit", "Burp Suite", "Incident Response",
                          "Firewalls", "IDS/IPS", "OSINT", "VAPT", "Threat Modeling"],
        "job_titles": ["Security Analyst", "Cybersecurity Engineer",
                       "SOC Analyst", "Security Consultant",
                       "Penetration Tester", "Security Trainee",
                       "Information Security Analyst"],
        "industries": ["IT Services", "BFSI", "Defense", "Government",
                       "Consulting", "Healthcare"],
        "degrees": ["bachelor", "btech", "master", "diploma"],
        "fields": ["Computer Science", "Information Technology", "Networking",
                   "Cybersecurity", "Electronics"],
        "certs": ["CEH (Certified Ethical Hacker)", "OSCP", "CompTIA Security+",
                  "CISSP", "CISM", "CompTIA CySA+"],
    },
    "Embedded Engineer": {
        "core_skills": ["C", "C++", "ARM Cortex", "RTOS", "UART", "SPI", "I2C",
                        "Linux Kernel", "Device Drivers", "Embedded Linux",
                        "Microcontrollers", "PCB", "Python", "Git", "AUTOSAR",
                        "FreeRTOS", "CAN Bus", "Bare Metal Programming",
                        "Oscilloscope", "Logic Analyzer", "STM32", "Arduino"],
        "distinguishing": "Works with HARDWARE and firmware. C/C++ on microcontrollers, RTOS, hardware protocols (UART, SPI, I2C, CAN). ECE/Electronics degree common. Distinguish from Systems Admin by writing firmware for hardware devices, not managing servers.",
        "fresher_skills": ["C", "C++", "Microcontrollers", "UART", "RTOS",
                           "Arduino", "Git"],
        "senior_skills": ["C", "C++", "ARM Cortex", "RTOS", "FreeRTOS",
                          "Linux Kernel", "Device Drivers", "AUTOSAR",
                          "CAN Bus", "SPI", "I2C", "Embedded Linux", "PCB"],
        "job_titles": ["Embedded Engineer", "Firmware Engineer",
                       "Embedded Systems Engineer", "IoT Engineer",
                       "Hardware-Software Engineer", "Junior Embedded Engineer",
                       "Embedded Trainee"],
        "industries": ["Automotive", "IoT", "Semiconductor", "Defense",
                       "Consumer Electronics", "Medical Devices", "Industrial"],
        "degrees": ["btech", "bachelor", "master", "mtech"],
        "fields": ["Electronics", "ECE", "Embedded Systems", "Computer Science",
                   "Electrical Engineering"],
        "certs": ["ARM Accredited Engineer", "AWS IoT Core", "AUTOSAR Certification",
                  "FreeRTOS Certification"],
    },
    "Game Developer": {
        "core_skills": ["Unity", "Unreal Engine", "C#", "C++", "3D Math",
                        "Game Physics", "Shaders", "AR/VR", "HLSL/GLSL",
                        "Game Design", "Blender", "Git", "Mobile Games",
                        "Pathfinding Algorithms", "Particle Systems",
                        "Multiplayer Networking", "Level Design", "UI in Unity"],
        "distinguishing": "Works on GAMES and interactive entertainment. Must have Unity or Unreal Engine as primary skill. C# (Unity) or C++ (Unreal) required. NO web dev, NO backend APIs. Completely distinct from Backend/Frontend/Full Stack.",
        "fresher_skills": ["Unity", "C#", "Game Design", "Blender", "Git"],
        "senior_skills": ["Unity", "Unreal Engine", "C#", "C++", "Shaders",
                          "AR/VR", "Game Physics", "HLSL", "Multiplayer Networking",
                          "Particle Systems", "Level Design"],
        "job_titles": ["Game Developer", "Unity Developer", "Game Programmer",
                       "Junior Game Developer", "Mobile Game Developer",
                       "Game Engineer", "Game Intern", "Gameplay Programmer"],
        "industries": ["Gaming", "AR/VR", "Edtech", "Entertainment",
                       "Simulation", "Defense Simulation"],
        "degrees": ["bachelor", "btech", "diploma", "master"],
        "fields": ["Computer Science", "Game Design", "Multimedia",
                   "Information Technology", "Animation"],
        "certs": ["Unity Certified Associate Game Developer",
                  "Unreal Online Learning Certified",
                  "Google Play Games Developer Certification"],
    },
    "Java Developer": {
        "core_skills": ["Java", "Spring Boot", "Spring Framework", "Hibernate",
                        "Maven", "Gradle", "Microservices", "REST API",
                        "PostgreSQL", "MySQL", "JUnit", "Docker", "Kafka",
                        "Git", "AWS", "Design Patterns", "Multithreading",
                        "JPA", "Spring Security", "Log4j", "Mockito"],
        "distinguishing": "Java is the PRIMARY language. Must have Spring Boot and Java. Like Backend Developer but exclusively Java-focused. If profile also has Python/Node.js as primary, it's likely Backend Developer or Full Stack. Strong BFSI/enterprise presence.",
        "fresher_skills": ["Java", "Spring Boot", "MySQL", "REST API",
                           "Git", "OOP", "JUnit"],
        "senior_skills": ["Java", "Spring Boot", "Hibernate", "Microservices",
                          "Kafka", "Docker", "JPA", "Spring Security",
                          "Design Patterns", "Multithreading", "PostgreSQL"],
        "job_titles": ["Java Developer", "Software Engineer", "Java Programmer",
                       "Backend Developer", "Java Software Engineer",
                       "Junior Java Developer", "J2EE Developer"],
        "industries": ["IT Services", "BFSI", "Product Startup", "Consulting",
                       "Telecom", "Insurance"],
        "degrees": ["bachelor", "btech", "mca", "master"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["Oracle Certified Java SE Programmer", "Spring Professional Certification",
                  "AWS Developer Associate"],
    },
    "Python Developer": {
        "core_skills": ["Python", "Django", "Flask", "FastAPI", "Celery",
                        "REST API", "PostgreSQL", "Redis", "Docker",
                        "Git", "Pytest", "SQLAlchemy", "Pandas", "Scripting",
                        "Web Scraping", "Airflow", "Linux", "BeautifulSoup",
                        "asyncio", "Pydantic"],
        "distinguishing": "Python is the PRIMARY and ONLY language. Unlike Backend Developer, no Java/Node.js. Unlike Data Scientist, no TensorFlow/ML models. Unlike Data Engineer, no Spark/Kafka. Pure Python scripting, automation, Django/Flask web apps.",
        "fresher_skills": ["Python", "Django", "MySQL", "REST API",
                           "Git", "Scripting", "Pandas"],
        "senior_skills": ["Python", "FastAPI", "Django", "Celery", "Redis",
                          "PostgreSQL", "Docker", "SQLAlchemy", "Airflow",
                          "asyncio", "Pytest", "Linux"],
        "job_titles": ["Python Developer", "Django Developer", "Software Developer",
                       "Backend Developer", "Automation Developer",
                       "Python Trainee", "Python Engineer"],
        "industries": ["IT Services", "AI Startup", "Analytics", "Fintech",
                       "Product Startup", "E-commerce"],
        "degrees": ["bachelor", "btech", "mca", "master", "diploma"],
        "fields": ["Computer Science", "Information Technology", "Data Science"],
        "certs": ["Python Institute PCEP / PCAP", "Django REST Framework Certified",
                  "AWS Developer Associate"],
    },
    "Node.js Developer": {
        "core_skills": ["JavaScript", "TypeScript", "Node.js", "Express.js",
                        "NestJS", "REST API", "GraphQL", "MongoDB", "PostgreSQL",
                        "Redis", "Docker", "Git", "Socket.IO", "JWT",
                        "Microservices", "bullmq", "PM2", "WebSockets", "Multer"],
        "distinguishing": "Node.js is PRIMARY server-side technology. JavaScript/TypeScript on the server. No Python. Distinguish from Full Stack by having NO frontend React/HTML/CSS. Distinguish from BackEnd Developer by Node.js being the core (not Python/Java).",
        "fresher_skills": ["Node.js", "Express.js", "JavaScript", "MongoDB",
                           "REST API", "Git"],
        "senior_skills": ["TypeScript", "NestJS", "Node.js", "PostgreSQL",
                          "Redis", "GraphQL", "Docker", "Socket.IO",
                          "Microservices", "JWT", "PM2", "MongoDB"],
        "job_titles": ["Node.js Developer", "Backend Developer",
                       "JavaScript Developer", "Software Developer",
                       "Server-side Developer", "Junior Node.js Developer"],
        "industries": ["IT Services", "Product Startup", "E-commerce", "SaaS",
                       "Fintech"],
        "degrees": ["bachelor", "btech", "diploma", "mca"],
        "fields": ["Computer Science", "Information Technology"],
        "certs": ["OpenJS Node.js Application Developer (JSNAD)",
                  "AWS Developer Associate", "MongoDB Certified Developer"],
    },
    "Solution Architect": {
        "core_skills": ["System Design", "AWS", "GCP", "Azure", "Microservices",
                        "Cloud Architecture", "Security", "Networking",
                        "Docker", "Kubernetes", "Database Design",
                        "High Availability", "Scalability", "Terraform",
                        "Cost Optimization", "Architecture Diagrams",
                        "API Design", "Event-Driven Architecture", "TOGAF"],
        "distinguishing": "Very senior role (8+ years). Designs ENTIRE SYSTEM ARCHITECTURES. Must have cloud certifications and cross-domain knowledge. Distinguish from Technical Lead by being architecture-first (not code), wider scope. Distinguish from Cloud Engineer by covering full-stack architecture decisions.",
        "fresher_skills": [],  # No freshers - min 7-8 years
        "senior_skills": ["System Design", "AWS", "Microservices", "Kubernetes",
                          "Terraform", "Cloud Architecture", "API Design",
                          "High Availability", "Database Design",
                          "Cost Optimization", "Security", "TOGAF"],
        "job_titles": ["Solution Architect", "Enterprise Architect",
                       "Cloud Architect", "Principal Engineer",
                       "Technical Architect", "Senior Solution Architect"],
        "industries": ["IT Services", "Consulting", "Fintech", "Telecom",
                       "Healthcare", "BFSI"],
        "degrees": ["bachelor", "btech", "master"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["AWS Solutions Architect Professional",
                  "Google Professional Cloud Architect",
                  "Azure Solutions Architect Expert (AZ-305)", "TOGAF Certified"],
    },
    "Technical Lead": {
        "core_skills": ["System Design", "Code Review", "Mentoring", "Agile",
                        "Python", "Java", "Microservices", "Docker",
                        "Kubernetes", "API Design", "Git", "CI/CD",
                        "Performance Optimization", "Technical Documentation",
                        "Sprint Planning", "Architecture Decision Records",
                        "Team Leadership", "Technical Interviews"],
        "distinguishing": "Senior role (6+ years). LEADS a team technically — code review, mentoring, sprint planning. Still writes code (unlike architect). Distinguish from Solution Architect by being more hands-on with code. Distinguish from Software Engineer by having leadership and mentoring responsibilities.",
        "fresher_skills": [],  # No freshers - min 5-6 years
        "senior_skills": ["System Design", "Code Review", "Mentoring",
                          "Python", "Microservices", "Docker", "Kubernetes",
                          "CI/CD", "Agile", "API Design", "Team Leadership",
                          "Performance Optimization"],
        "job_titles": ["Technical Lead", "Tech Lead", "Lead Software Engineer",
                       "Engineering Manager", "Senior Software Engineer (Lead)",
                       "Principal Developer"],
        "industries": ["IT Services", "Product Startup", "Consulting", "Fintech",
                       "E-commerce"],
        "degrees": ["bachelor", "btech", "master"],
        "fields": ["Computer Science", "Information Technology", "Software Engineering"],
        "certs": ["PMP", "Scrum Master (CSM)", "AWS Solutions Architect Associate",
                  "CKA"],
    },
    "Database Administrator": {
        "core_skills": ["PostgreSQL", "MySQL", "Oracle DB", "SQL Server",
                        "Database Design", "Backup and Recovery",
                        "Performance Tuning", "Replication", "Linux",
                        "SQL", "MongoDB", "Redis", "Shell Scripting", "PL/SQL",
                        "High Availability", "Database Security", "RMAN",
                        "Index Optimization", "Partitioning", "JSON in SQL"],
        "distinguishing": "Focus is MANAGING and optimizing databases — not writing apps. Has deep SQL/PL-SQL, performance tuning, backup/recovery skills. Distinguish from Backend Developer by not writing application code. Often found in BFSI and government sectors in India.",
        "fresher_skills": ["SQL", "MySQL", "PostgreSQL", "Database Design",
                           "Backup and Recovery", "Linux"],
        "senior_skills": ["Oracle DB", "SQL Server", "PostgreSQL",
                          "Performance Tuning", "Replication", "PL/SQL",
                          "High Availability", "RMAN", "Index Optimization",
                          "Shell Scripting", "Database Security"],
        "job_titles": ["Database Administrator", "DBA", "SQL Developer",
                       "Database Engineer", "Oracle DBA",
                       "Junior DBA", "Database Analyst"],
        "industries": ["IT Services", "BFSI", "Healthcare", "Government",
                       "Retail", "Telecom"],
        "degrees": ["bachelor", "btech", "mca", "diploma"],
        "fields": ["Computer Science", "Information Technology",
                   "Database Management"],
        "certs": ["Oracle Database Administrator Certified",
                  "Microsoft SQL Server Database Administrator",
                  "AWS Database Specialty", "MongoDB DBA Certification"],
    },
    "Network Engineer": {
        "core_skills": ["Cisco", "Routing", "Switching", "OSPF", "BGP",
                        "MPLS", "VPN", "Firewalls", "Linux", "TCP/IP",
                        "Wireshark", "Network Security", "Python",
                        "Cloud Networking", "SD-WAN", "QoS", "EIGRP",
                        "NAT", "Network Monitoring", "F5 Load Balancer"],
        "distinguishing": "Physical and logical NETWORK infrastructure. Cisco routers/switches, routing protocols (OSPF, BGP, EIGRP), VPN, Firewalls. ECE degree common. Distinguish from System Admin by not managing servers. Distinguish from Cybersecurity by not being security-offensive focused — more ops/maintenance.",
        "fresher_skills": ["Routing", "Switching", "TCP/IP", "Cisco",
                           "Wireshark", "Network Monitoring"],
        "senior_skills": ["Cisco", "BGP", "OSPF", "MPLS", "SD-WAN",
                          "Firewalls", "VPN", "Python", "Cloud Networking",
                          "QoS", "F5 Load Balancer", "Network Security"],
        "job_titles": ["Network Engineer", "Network Administrator",
                       "NOC Engineer", "Network Operations Engineer",
                       "Junior Network Engineer", "Network Trainee",
                       "Infrastructure Engineer"],
        "industries": ["Telecom", "IT Services", "ISP", "Defense",
                       "Government", "Banking", "Healthcare"],
        "degrees": ["btech", "bachelor", "diploma", "mtech"],
        "fields": ["ECE", "Networking", "Computer Science",
                   "Information Technology", "Electrical Engineering"],
        "certs": ["CCNA (Cisco Certified Network Associate)",
                  "CCNP (Cisco Certified Network Professional)",
                  "CompTIA Network+", "Juniper JNCIA", "Palo Alto PCNSA"],
    },
    "Systems Administrator": {
        "core_skills": ["Linux", "Windows Server", "Active Directory",
                        "Shell Scripting", "Python", "VMware", "Ansible",
                        "Monitoring", "Backup", "Networking", "DNS",
                        "DHCP", "AWS", "Docker", "Git",
                        "Patch Management", "LDAP", "NFS", "Cron Jobs",
                        "System Performance Tuning"],
        "distinguishing": "Manages ON-PREMISE servers and OS. Linux admin, Windows Server, Active Directory, VMware. Distinguish from DevOps by not owning CI/CD pipelines or containers primarily. Distinguish from Cloud Engineer by managing physical/on-premise servers (though may also have AWS basics).",
        "fresher_skills": ["Linux", "Windows Server", "Networking",
                           "Shell Scripting", "DNS", "DHCP"],
        "senior_skills": ["Linux", "Active Directory", "VMware", "Ansible",
                          "Shell Scripting", "Monitoring", "Backup",
                          "DNS", "DHCP", "Patch Management", "AWS", "Docker"],
        "job_titles": ["Systems Administrator", "Linux Administrator",
                       "IT Administrator", "Infrastructure Engineer",
                       "System Engineer", "Junior Sysadmin", "IT Support Engineer"],
        "industries": ["IT Services", "BPO", "Healthcare", "Education",
                       "Government", "Manufacturing"],
        "degrees": ["bachelor", "btech", "diploma", "mca"],
        "fields": ["Computer Science", "Information Technology", "Networking"],
        "certs": ["RHCE (Red Hat Certified Engineer)",
                  "CompTIA Linux+ / A+",
                  "Microsoft MCSA",
                  "VMware VCP",
                  "AWS SysOps Administrator Associate"],
    },
    "AI Research Engineer": {
        "core_skills": ["Python", "PyTorch", "TensorFlow", "Transformers",
                        "NLP", "Computer Vision", "Reinforcement Learning",
                        "LLM Fine-tuning", "Hugging Face", "CUDA",
                        "Mathematics", "Research Papers", "LaTeX",
                        "ONNX", "MLflow", "JAX", "Diffusion Models",
                        "RAG", "Vector Databases", "GPT Fine-tuning"],
        "distinguishing": "Focused on RESEARCH and advancing AI — reads/publishes papers, works on SOTA models. More academic than ML Engineer. Must have deep maths and research paper skills. Distinguish from ML Engineer by being research-first (not production deployment). Fewer freshers, more masters/PhD.",
        "fresher_skills": ["Python", "PyTorch", "Mathematics",
                           "NLP", "Deep Learning", "Research Papers"],
        "senior_skills": ["PyTorch", "Transformers", "LLM Fine-tuning",
                          "Hugging Face", "CUDA", "RAG", "Diffusion Models",
                          "Computer Vision", "JAX", "ONNX", "Vector Databases",
                          "Research Papers", "LaTeX"],
        "job_titles": ["AI Research Engineer", "Research Scientist",
                       "ML Researcher", "Applied Scientist",
                       "Junior AI Researcher", "AI Intern",
                       "Deep Learning Researcher"],
        "industries": ["AI Startup", "Research Lab", "Academia",
                       "Big Tech India (Google India, Microsoft India)",
                       "Pharmaceutical AI"],
        "degrees": ["master", "phd", "bachelor"],
        "fields": ["Computer Science", "Artificial Intelligence", "Mathematics",
                   "Statistics", "Physics"],
        "certs": ["Deep Learning Specialization (deeplearning.ai)",
                  "Hugging Face NLP Course",
                  "AWS Certified ML Specialty",
                  "Google Cloud Professional ML Engineer"],
    },
    "Technical Writer": {
        "core_skills": ["Technical Writing", "API Documentation",
                        "Markdown", "Confluence", "JIRA", "Git",
                        "Content Strategy", "User Manuals",
                        "DITA", "XML", "Swagger/OpenAPI",
                        "Research", "Information Architecture",
                        "Docs-as-Code", "Readme.io", "Postman (for API testing)",
                        "Editing", "Style Guides"],
        "distinguishing": "Creates DOCUMENTATION — API docs, user manuals, developer guides. NO code production. Different from all developer roles. Skills are writing + tooling (Confluence, JIRA, Swagger). Often has English/Communication + CS background.",
        "fresher_skills": ["Technical Writing", "Markdown", "Confluence",
                           "JIRA", "User Manuals", "Research"],
        "senior_skills": ["Technical Writing", "API Documentation",
                          "Swagger/OpenAPI", "DITA", "Markdown",
                          "Information Architecture", "Docs-as-Code",
                          "Content Strategy", "Git", "Style Guides"],
        "job_titles": ["Technical Writer", "Content Developer",
                       "Documentation Specialist", "API Documentation Writer",
                       "Knowledge Base Author", "Junior Technical Writer",
                       "Documentation Engineer"],
        "industries": ["IT Services", "Product Startup", "SaaS",
                       "Telecom", "Healthcare IT", "Gaming"],
        "degrees": ["bachelor", "master", "diploma"],
        "fields": ["English", "Computer Science", "Communication",
                   "Information Technology", "Journalism"],
        "certs": ["Google Technical Writing Fundamentals",
                  "STC Certified Technical Communicator (CTC)",
                  "API Documentation Certification (Udemy)"],
    },
    "Salesforce Developer": {
        "core_skills": ["Salesforce", "Apex", "Visualforce", "LWC",
                        "SOQL", "Salesforce CRM",
                        "Sales Cloud", "Service Cloud",
                        "Flows", "Process Builder", "REST API",
                        "Integration", "Git", "Salesforce Admin",
                        "Objects and Fields", "Triggers", "Batch Apex",
                        "Salesforce DX", "CPQ"],
        "distinguishing": "Works EXCLUSIVELY on Salesforce platform. Must have Apex, LWC, SOQL. No general web dev skills. Only Salesforce-specific development. Strong in BFSI, Consulting, Retail sectors. Certifications are very important signal.",
        "fresher_skills": ["Salesforce", "Apex", "SOQL",
                           "Salesforce Admin", "Visualforce"],
        "senior_skills": ["Apex", "LWC", "SOQL", "Flows",
                          "Integration", "Sales Cloud", "Service Cloud",
                          "Batch Apex", "Triggers", "Salesforce DX", "CPQ"],
        "job_titles": ["Salesforce Developer", "CRM Developer",
                       "Salesforce Admin", "Salesforce Consultant",
                       "Junior Salesforce Developer", "Salesforce Engineer"],
        "industries": ["IT Services", "Consulting", "BFSI",
                       "Healthcare", "Retail", "Manufacturing"],
        "degrees": ["bachelor", "btech", "mca", "master"],
        "fields": ["Computer Science", "Information Technology",
                   "Business Administration"],
        "certs": ["Salesforce Certified Platform Developer I",
                  "Salesforce Certified Administrator",
                  "Salesforce Certified Platform Developer II",
                  "Salesforce Certified JavaScript Developer I"],
    },
    "ERP Consultant": {
        "core_skills": ["SAP", "SAP ABAP", "SAP FICO", "SAP MM",
                        "SAP SD", "Oracle ERP", "SAP S/4HANA",
                        "Business Process", "SQL",
                        "Requirements Gathering",
                        "Stakeholder Management",
                        "Excel", "Data Migration", "SAP BASIS",
                        "Microsoft Dynamics", "SAP BW", "LSMW"],
        "distinguishing": "Works on ERP platforms (SAP, Oracle, Microsoft Dynamics). SAP is very strong signal. Has both functional (business process) and technical (ABAP, configuration) skills. Common in Manufacturing, Retail, BFSI. Distinguish from Business Analyst by ERP-platform specificity.",
        "fresher_skills": ["SAP", "SAP FICO", "SAP MM", "SQL",
                           "Business Process", "Excel"],
        "senior_skills": ["SAP ABAP", "SAP S/4HANA", "SAP FICO", "SAP MM",
                          "SAP SD", "Data Migration", "Requirements Gathering",
                          "SAP BW", "Microsoft Dynamics",
                          "Stakeholder Management", "LSMW"],
        "job_titles": ["SAP Consultant", "ERP Consultant",
                       "SAP Functional Consultant", "SAP ABAP Developer",
                       "Oracle ERP Consultant", "SAP Analyst",
                       "Junior SAP Consultant", "SAP Trainee"],
        "industries": ["IT Services", "Consulting", "Manufacturing",
                       "Retail", "BFSI", "Pharma", "Logistics"],
        "degrees": ["bachelor", "master", "mba", "btech"],
        "fields": ["Business Administration", "Computer Science",
                   "Commerce", "Management", "Supply Chain"],
        "certs": ["SAP Certified Application Associate (S/4HANA)",
                  "SAP Certified Development Associate (ABAP)",
                  "Oracle ERP Cloud Certified",
                  "SAP S/4HANA Sourcing and Procurement"],
    },
}

ALL_CAREERS = list(CAREER_PROFILES.keys())


# ─────────────────────────────────────────────────────────────────────────────
# JSON SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = {
    "profile_id": "string — unique, e.g. 'p001'",
    "skills": "array of strings — plain skill names, e.g. ['Python', 'Django']",
    "experience_years": "float — total years 0.0 to 18.0",
    "current_job_title": "string — current/most recent job title",
    "education_degree": "string — one of: bachelor, master, phd, diploma, btech, mtech, mca",
    "field_of_study": "string — e.g. 'Computer Science', 'ECE', 'Mathematics'",
    "certifications": "array of strings — certification names (may be empty [])",
    "industry": "string — company industry, e.g. 'IT Services', 'Fintech'",
    "target_career": "string — MUST be exactly one of the 30 allowed career labels",
}


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_prompt(careers: list[str], count_per_career: int) -> str:
    career_list_str = "\n".join(f"  - {c}" for c in careers)
    schema_str = json.dumps(SCHEMA, indent=4)
    total = len(careers) * count_per_career

    # ── Full per-career reference blocks (ALL fields, no truncation) ──────
    career_blocks = []
    for career in careers:
        p = CAREER_PROFILES[career]
        all_skills = ", ".join(p["core_skills"])
        job_titles = ", ".join(p["job_titles"])
        industries = ", ".join(p["industries"])
        degrees = ", ".join(p["degrees"])
        fields = ", ".join(p["fields"])
        certs = ", ".join(p["certs"])
        fresher = ", ".join(p.get("fresher_skills", [])) or "N/A (senior-only career)"
        senior = ", ".join(p.get("senior_skills", []))
        distinguishing = p.get("distinguishing", "")

        block = f"""  ┌─ {career}
  │  DISTINGUISHING: {distinguishing}
  │  ALL VALID SKILLS: {all_skills}
  │  FRESHER SKILL SAMPLE (0-1yr): {fresher}
  │  SENIOR SKILL SAMPLE (6+yr): {senior}
  │  VALID JOB TITLES: {job_titles}
  │  VALID INDUSTRIES: {industries}
  │  VALID DEGREES: {degrees}
  │  VALID FIELDS OF STUDY: {fields}
  │  VALID CERTIFICATIONS: {certs}
  └──────────────────────────────────────────────────────────"""
        career_blocks.append(block)

    career_reference = "\n".join(career_blocks)

    # ── Multiple diverse example profiles ────────────────────────────────
    examples = json.dumps([
        {
            "profile_id": "p0001",
            "skills": ["Python", "Django", "PostgreSQL", "REST API", "Git"],
            "experience_years": 0.5,
            "current_job_title": "Software Trainee",
            "education_degree": "btech",
            "field_of_study": "Computer Science",
            "certifications": [],
            "industry": "IT Services",
            "target_career": "Backend Developer",
        },
        {
            "profile_id": "p0002",
            "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Redis",
                       "Celery", "RabbitMQ", "Docker", "REST API", "JWT", "Git", "Linux"],
            "experience_years": 4.5,
            "current_job_title": "Backend Engineer",
            "education_degree": "master",
            "field_of_study": "Computer Science",
            "certifications": ["AWS Developer Associate"],
            "industry": "Fintech",
            "target_career": "Backend Developer",
        },
        {
            "profile_id": "p0003",
            "skills": ["Unity", "C#", "Game Design", "Blender", "Git"],
            "experience_years": 0.0,
            "current_job_title": "Game Developer Intern",
            "education_degree": "btech",
            "field_of_study": "Computer Science",
            "certifications": [],
            "industry": "Gaming",
            "target_career": "Game Developer",
        },
        {
            "profile_id": "p0004",
            "skills": ["SQL", "Power BI", "Excel", "Python", "Pandas",
                       "Tableau", "Statistics", "Business Analysis", "DAX"],
            "experience_years": 3.0,
            "current_job_title": "Data Analyst",
            "education_degree": "bachelor",
            "field_of_study": "Statistics",
            "certifications": ["Google Data Analytics Professional"],
            "industry": "BFSI",
            "target_career": "Data Analyst",
        },
        {
            "profile_id": "p0005",
            "skills": ["Apex", "LWC", "SOQL", "Salesforce CRM", "Salesforce Admin",
                       "Visualforce", "Flows", "REST API", "Integration", "Git"],
            "experience_years": 2.0,
            "current_job_title": "Salesforce Developer",
            "education_degree": "btech",
            "field_of_study": "Information Technology",
            "certifications": ["Salesforce Certified Platform Developer I"],
            "industry": "Consulting",
            "target_career": "Salesforce Developer",
        },
    ], indent=2)

    return f"""
You are generating a high-quality labeled training dataset for an ML career prediction model serving the Indian job market.

════════════════════════════════════════════════════════════
TASK
════════════════════════════════════════════════════════════
Generate exactly {total} professional profiles: {count_per_career} per career label.
  - Career labels in this batch : {len(careers)}
  - Profiles per career         : {count_per_career}
  - Grand total profiles        : {total}

════════════════════════════════════════════════════════════
ALLOWED CAREER LABELS  (exact values for "target_career")
════════════════════════════════════════════════════════════
{career_list_str}

════════════════════════════════════════════════════════════
PROFILE JSON SCHEMA
════════════════════════════════════════════════════════════
{schema_str}

════════════════════════════════════════════════════════════
PER-CAREER REFERENCE  (use this to generate each career's profiles)
════════════════════════════════════════════════════════════
For every career below you have:
  - DISTINGUISHING: what makes this career DISTINCT from similar ones
  - ALL VALID SKILLS: the complete skill pool to pick from
  - FRESHER / SENIOR samples: skill sets typical at each level
  - VALID JOB TITLES / INDUSTRIES / DEGREES / FIELDS / CERTS

{career_reference}

════════════════════════════════════════════════════════════
MANDATORY RULES — FOLLOW ALL OF THEM
════════════════════════════════════════════════════════════

RULE 1 — SEMANTIC CONSISTENCY (most important)
  - Skills MUST be drawn from the "ALL VALID SKILLS" list for that career.
  - NEVER assign Game Developer skills (Unity, C#, Game Physics) to any non-game career.
  - NEVER assign Data Scientist skills (TensorFlow, PyTorch, ML) to a Backend/Java Developer.
  - NEVER assign Figma/Adobe XD to a Backend Developer or DevOps Engineer.
  - NEVER assign Kubernetes/Docker as PRIMARY skills to a Data Analyst or QA Engineer (manual).
  - Refer to "DISTINGUISHING" to understand what separates similar careers.

RULE 2 — SKILL COUNT BY EXPERIENCE LEVEL
  - Fresher  (0.0 – 1.0 yr)  : 3–5  skills  (use FRESHER SKILL SAMPLE as guide)
  - Junior   (1.0 – 3.0 yr)  : 5–8  skills
  - Mid      (3.0 – 6.0 yr)  : 7–11 skills
  - Senior   (6.0 – 15.0 yr) : 10–16 skills (use SENIOR SKILL SAMPLE as guide)

RULE 3 — EXPERIENCE DISTRIBUTION PER CAREER
  For each career generate approximately:
  - 15 % freshers  (0.0 – 1.0  yr)
  - 35 % junior    (1.0 – 3.0  yr)
  - 30 % mid       (3.0 – 6.5  yr)
  - 20 % senior    (6.5 – 15.0 yr)
  Exception: Solution Architect and Technical Lead have NO freshers — minimum 6 years.

RULE 4 — JOB TITLE MUST MATCH CAREER AND EXPERIENCE
  - Freshers: use "Trainee", "Intern", "Junior", or "Fresher" in the title.
  - Senior: use "Senior", "Lead", "Principal", or "Manager" in the title.
  - ONLY use job titles from the "VALID JOB TITLES" list for that career.
  - The job title must make sense with the skills (e.g., a "Game Developer" must not have SQL/Excel as primary skills).

RULE 5 — EDUCATION DEGREE VALUES
  Use exactly one of: bachelor | master | phd | diploma | btech | mtech | mca
  Match degree to what's realistic for the career (e.g., AI Research often has master/phd).

RULE 6 — CERTIFICATIONS
  - 35 % of profiles may have empty certifications [].
  - When non-empty, pick 1–2 certs from the "VALID CERTIFICATIONS" list for that career.
  - Do NOT invent certifications that don't exist.

RULE 7 — INDUSTRY
  Pick from the "VALID INDUSTRIES" for that career. Must be India-realistic.

RULE 8 — PROFILE ID UNIQUENESS
  Profile IDs must be globally unique across the entire output: p0001, p0002, p0003, …

RULE 9 — OUTPUT FORMAT
  Pure JSON array ONLY. No markdown fences, no explanation, no comments.
  Start directly with [ and end with ]

RULE 10 — CAREER DISAMBIGUATION (for similar careers)
  Backend Developer  vs  Python Developer  : Back-end is polyglot (Python+Node.js OK); Python Dev is Python-only.
  Backend Developer  vs  Java Developer     : Java Dev uses Java+Spring Boot exclusively.
  Backend Developer  vs  Node.js Developer  : Node.js Dev uses JS/TS on server exclusively.
  Full Stack         vs  Backend Developer  : Full Stack MUST have frontend (HTML/CSS/React) AND backend.
  DevOps             vs  Cloud Engineer     : DevOps owns CI/CD pipelines; Cloud owns provisoning/IAM.
  DevOps             vs  Systems Admin      : Systems Admin manages on-premise OS; DevOps uses containers/IaC.
  Data Scientist     vs  ML Engineer        : DS focuses on analysis/statistics; MLE focuses on productionizing models.
  Data Scientist     vs  Data Analyst       : DS builds ML models; DA creates reports/dashboards only.
  Data Engineer      vs  Data Analyst       : DE builds pipelines (Spark/Kafka); DA consumes the data.
  AI Research Eng    vs  ML Engineer        : AI Research publishes/reads papers, academic focus; MLE ships production.
  Solution Architect vs  Technical Lead     : Architect designs systems broadly; Tech Lead leads team + writes code.
  Cybersecurity Eng  vs  Network Engineer   : CyberSec does pen-testing/SOC; Network does routing/switching.
  Android Developer  vs  iOS Developer      : Strictly separate by platform (Kotlin vs Swift).
  Salesforce Dev     vs  ERP Consultant     : Salesforce Dev writes Apex/LWC; ERP is SAP/Oracle functional/technical.

════════════════════════════════════════════════════════════
DIVERSE EXAMPLE PROFILES (5 examples showing variety)
════════════════════════════════════════════════════════════
{examples}

════════════════════════════════════════════════════════════
GENERATE THE DATASET NOW
════════════════════════════════════════════════════════════
Generate {total} profiles as a single JSON array.
Process careers in this exact order: {', '.join(careers)}.
Within each career, vary experience levels as described in RULE 3.
"""


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Print LLM prompt for generating career training data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python generate_data_prompt.py                           # Full 30-career prompt
  python generate_data_prompt.py --career "Data Scientist" # Single career
  python generate_data_prompt.py --list                    # List all 30 careers
  python generate_data_prompt.py --schema                  # JSON schema only
  python generate_data_prompt.py --count 50                # 50 samples per career
  python generate_data_prompt.py --count 70 > prompt.txt   # Save to file
""",
    )
    parser.add_argument(
        "--career",
        type=str,
        default=None,
        help="Generate prompt for a single career only",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=70,
        help="Number of profiles per career class (default: 70)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all 30 career classes and exit",
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print JSON schema only and exit",
    )
    args = parser.parse_args()

    if args.list:
        print("30 Career Classes:")
        for i, c in enumerate(ALL_CAREERS, 1):
            print(f"  {i:2d}. {c}")
        return

    if args.schema:
        print("Training Profile JSON Schema:")
        print(json.dumps(SCHEMA, indent=2))
        return

    if args.career:
        matched = [c for c in ALL_CAREERS if c.lower() == args.career.lower()]
        if not matched:
            print(f"ERROR: Career '{args.career}' not found.", file=sys.stderr)
            print("Run with --list to see valid career names.", file=sys.stderr)
            sys.exit(1)
        careers = matched
    else:
        careers = ALL_CAREERS

    prompt = build_prompt(careers, args.count)
    print(prompt)

    print(
        f"\n\n# ─── SAVE INSTRUCTIONS ───────────────────────────────────────────\n"
        f"# 1. Copy the prompt above.\n"
        f"# 2. Paste into ChatGPT-4o / Claude / Gemini.\n"
        f"# 3. Save the raw JSON response to:\n"
        f"#       training/data/batch_001.json   (first batch)\n"
        f"#       training/data/batch_002.json   (second batch, more data)\n"
        f"# 4. Then run:  python training/train_career_model.py\n"
        f"# ─────────────────────────────────────────────────────────────────\n",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
