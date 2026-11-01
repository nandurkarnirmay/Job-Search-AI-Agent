"""Skills taxonomy for the Indian job market (tech, data, core engineering, business).
Each skill has a canonical name and aliases; matching respects symbols like C++, C#, .NET and Node.js and avoids
false hits ("java" inside "javascript", "sql" inside "mysql"). Pure functions."""
import re
from functools import lru_cache

# canonical -> aliases (lowercase). Ambiguous single letters (C, R, Go) only match in unambiguous forms, and
# everyday words are avoided (no bare "spark": spark plugs; no "rails": guard rails; no "containers").
SKILLS: dict[str, list[str]] = {
    # programming
    "Python": ["python"], "Java": ["java", "core java", "java 8", "java 11", "java 17"],
    "JavaScript": ["javascript", "js", "es6"], "TypeScript": ["typescript"],
    "C++": ["c++", "cpp"], "C": ["c programming", "c language", "embedded c", "c/c++"], "C#": ["c#", "csharp"],
    "Go": ["golang", "go language"], "Rust": ["rust"], "Kotlin": ["kotlin"], "Swift": ["swift"], "PHP": ["php"],
    "Ruby": ["ruby", "ruby on rails"], "Scala": ["scala"],
    "R": ["r programming", "r language", "rstudio", "r studio"], "MATLAB": ["matlab"], "Simulink": ["simulink"],
    "Bash": ["bash", "shell scripting", "shell script"],
    # web
    "React": ["react", "react.js", "reactjs"], "Next.js": ["next.js", "nextjs"], "Angular": ["angular", "angularjs"],
    "Vue": ["vue", "vue.js", "vuejs"], "Node.js": ["node.js", "nodejs", "node"], "Express": ["express", "express.js"],
    "Django": ["django"], "Flask": ["flask"], "FastAPI": ["fastapi"], "Spring Boot": ["spring boot", "springboot"],
    "Spring": ["spring", "spring mvc"], "Hibernate": ["hibernate", "jpa"], ".NET": [".net", "asp.net", "dotnet"],
    "HTML": ["html", "html5"], "CSS": ["css", "css3", "tailwind", "bootstrap", "sass"],
    "REST APIs": ["rest api", "rest apis", "restful", "rest"], "GraphQL": ["graphql"], "Microservices": ["microservices"],
    # data
    "SQL": ["sql", "t-sql", "pl/sql", "plsql"], "MySQL": ["mysql"], "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"], "Redis": ["redis"], "Oracle": ["oracle db", "oracle database"],
    "Excel": ["excel", "ms excel", "advanced excel", "vlookup", "pivot tables", "pivot table"],
    "VBA": ["vba", "excel macros", "macros"],
    "Power BI": ["power bi", "powerbi"], "Tableau": ["tableau"], "Looker": ["looker"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Statistics": ["statistics", "statistical analysis", "hypothesis testing"],
    "Machine Learning": ["machine learning", "ml"], "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"], "Computer Vision": ["computer vision", "opencv"],
    "Generative AI": ["generative ai", "genai", "llm", "llms", "large language models", "rag", "langchain", "langgraph"],
    "TensorFlow": ["tensorflow", "keras"], "PyTorch": ["pytorch"], "scikit-learn": ["scikit-learn", "sklearn"],
    "Spark": ["pyspark", "apache spark", "spark sql", "databricks"], "Hadoop": ["hadoop", "hive"], "Airflow": ["airflow"],
    "ETL": ["etl", "data pipelines", "data pipeline"], "Data Analysis": ["data analysis", "data analytics"],
    "Data Visualization": ["data visualization", "data visualisation", "dashboards", "dashboarding"],
    # cloud / devops
    "AWS": ["aws", "amazon web services", "ec2", "aws lambda"], "Azure": ["azure"], "GCP": ["gcp", "google cloud"],
    "Docker": ["docker", "containerization"], "Kubernetes": ["kubernetes", "k8s"], "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "cicd", "jenkins", "github actions", "gitlab ci"], "Git": ["git", "github", "gitlab"],
    "Linux": ["linux", "unix"], "Kafka": ["kafka"],
    # testing / practices
    "Unit Testing": ["unit testing", "junit", "pytest", "jest"], "Selenium": ["selenium"],
    "Agile": ["agile", "scrum", "jira"], "DSA": ["data structures", "algorithms", "dsa"],
    "System Design": ["system design", "low level design", "high level design", "lld", "hld"],
    "OOP": ["oop", "oops", "object oriented", "object-oriented"],
    # mobile
    "Android": ["android"], "iOS": ["ios"], "Flutter": ["flutter", "dart"], "React Native": ["react native"],
    # core engineering (mechanical / civil / electrical)
    "AutoCAD": ["autocad", "auto cad"], "SolidWorks": ["solidworks", "solid works"], "CATIA": ["catia"],
    "Creo": ["creo", "pro/e", "pro-e", "proe"], "NX": ["siemens nx", "unigraphics"], "ANSYS": ["ansys"],
    "FEA": ["fea", "finite element", "finite element analysis"], "CFD": ["cfd", "computational fluid dynamics", "fluent"],
    "GD&T": ["gd&t", "gdt", "geometric dimensioning"], "Thermodynamics": ["thermodynamics"],
    "Heat Transfer": ["heat transfer"], "Fluid Mechanics": ["fluid mechanics"], "HVAC": ["hvac"],
    "Piping": ["piping", "pipe sizing", "piping design"], "ASME Codes": ["asme"],
    "Manufacturing": ["manufacturing", "production planning", "cnc", "machining"],
    "Lean / Six Sigma": ["six sigma", "lean manufacturing", "lean", "kaizen", "5s"],
    "Quality Control": ["quality control", "quality assurance", "qc", "spc", "ppap", "apqp", "fmea"],
    "PLC / SCADA": ["plc", "scada"], "STAAD Pro": ["staad", "staad pro", "staad.pro"], "Revit": ["revit"],
    "Metallurgy": ["metallurgy", "materials science", "heat treatment"], "Welding": ["welding"],
    # business
    "SAP": ["sap", "sap fico", "sap mm", "sap sd", "sap pp"], "Tally": ["tally", "tally erp", "tally prime"],
    "GST": ["gst", "goods and services tax"], "Accounting": ["accounting", "bookkeeping", "accounts payable"],
    "Financial Analysis": ["financial analysis", "financial modelling", "financial modeling"],
    "Sales": ["sales", "b2b sales", "inside sales"], "Digital Marketing": ["digital marketing", "seo", "sem",
                                                                         "google ads", "social media marketing"],
    "CRM": ["crm", "salesforce", "hubspot", "zoho crm"], "Communication": ["communication skills", "communication"],
    "Project Management": ["project management", "pmp"], "Stakeholder Management": ["stakeholder management"],
    "Figma": ["figma"], "UI/UX": ["ui/ux", "ux design", "ui design", "user experience"],
}

# a specific skill implies its parent (MySQL experience counts for an "SQL" requirement)
IMPLIES: dict[str, list[str]] = {
    "MySQL": ["SQL"], "PostgreSQL": ["SQL"], "Oracle": ["SQL"], "Pandas": ["Python"], "NumPy": ["Python"],
    "Django": ["Python"], "Flask": ["Python"], "FastAPI": ["Python"], "PyTorch": ["Python", "Deep Learning"],
    "TensorFlow": ["Python", "Deep Learning"], "scikit-learn": ["Machine Learning"], "Spring Boot": ["Java", "Spring"],
    "Hibernate": ["Java"], "React": ["JavaScript"], "Next.js": ["React", "JavaScript"], "Angular": ["JavaScript"],
    "Vue": ["JavaScript"], "Node.js": ["JavaScript"], "Express": ["Node.js", "JavaScript"],
    "TypeScript": ["JavaScript"], "Deep Learning": ["Machine Learning"], "NLP": ["Machine Learning"],
    "Computer Vision": ["Machine Learning"], "Kubernetes": ["Docker"], "Power BI": ["Data Visualization"],
    "Tableau": ["Data Visualization"], "Simulink": ["MATLAB"], "VBA": ["Excel"], "React Native": ["React"],
}

_EDGE_L = r"(?<![a-z0-9+#])"
_EDGE_R = r"(?![a-z0-9+#])"


@lru_cache
def _patterns() -> list[tuple[str, re.Pattern]]:
    out = []
    for canonical, aliases in SKILLS.items():
        alts = sorted({a.lower() for a in aliases}, key=len, reverse=True)
        body = "|".join(re.escape(a).replace(r"\ ", r"[\s\-]?") for a in alts)
        out.append((canonical, re.compile(f"{_EDGE_L}(?:{body}){_EDGE_R}", re.I)))
    return out


# words that are skills only in context; "node" alone is too ambiguous, so require a tech neighbour
_AMBIGUOUS = {"Node.js": re.compile(r"(?<![a-z0-9+#])node(?![a-z0-9+#.])", re.I),
              "Spring": re.compile(r"(?<![a-z0-9+#])spring(?![a-z0-9+#])", re.I),
              "Lean / Six Sigma": re.compile(r"(?<![a-z0-9])lean(?![a-z0-9])", re.I),
              "Swift": re.compile(r"(?<![a-z0-9])swift(?![a-z0-9])", re.I),
              "Rust": re.compile(r"(?<![a-z0-9])rust(?![a-z0-9])", re.I),
              "Communication": re.compile(r"(?<![a-z0-9])communication(?![a-z0-9 ]*skills)", re.I),
              "REST APIs": re.compile(r"(?<![a-z0-9])rest(?![a-z0-9 ]*(?:api|apis|ful))", re.I),
              "Sales": re.compile(r"(?<![a-z0-9])sales(?![a-z0-9 ]*(?:force))", re.I)}
_STRONG = {"Node.js": ["node.js", "nodejs"], "Spring": ["spring boot", "spring mvc", "springboot"],
           "Lean / Six Sigma": ["six sigma", "lean manufacturing", "kaizen"], "Swift": ["swiftui", "ios"],
           "Rust": ["rustlang", "cargo"], "Communication": ["communication skills"],
           "REST APIs": ["rest api", "rest apis", "restful"], "Sales": ["b2b sales", "inside sales", "sales target"]}
_TECH_CONTEXT = re.compile(r"(?<![a-z0-9])(developer|engineer|programming|framework|backend|frontend|software|"
                           r"language|ios|apple|api|server|web)(?![a-z0-9])", re.I)


_SPARK_BARE = re.compile(r"(?<![a-z0-9])spark(?![a-z0-9])(?!\s*plugs?)", re.I)
_DATA_CONTEXT = re.compile(r"(?<![a-z0-9])(hadoop|hive|big data|data engineer\w*|etl|scala|kafka|data pipelines?|"
                           r"databricks|airflow)(?![a-z0-9])", re.I)


def extract_skills(text: str, *, with_implied: bool = True) -> list[str]:
    """Canonical skills mentioned in text, in taxonomy order."""
    t = text.lower()
    found = []
    if _SPARK_BARE.search(t) and _DATA_CONTEXT.search(t):
        found.append("Spark")  # bare "Spark" next to Hadoop/ETL/big data is Apache Spark, not a spark plug
    for canonical, pat in _patterns():
        if not pat.search(t):
            continue
        if canonical in _AMBIGUOUS:
            strong = any(s in t for s in _STRONG[canonical])
            only_bare = not strong and _AMBIGUOUS[canonical].search(t)
            if only_bare and canonical in {"Node.js", "Spring", "Swift", "Rust"} and not _TECH_CONTEXT.search(t):
                continue  # "spring internship", "rust-proof coating": no tech context, not a skill
            if only_bare and canonical in {"Lean / Six Sigma", "Communication", "REST APIs", "Sales"}:
                continue  # bare words like "lean", "rest", "sales" are too common to count
        if canonical not in found:
            found.append(canonical)
    if with_implied:
        for s in list(found):
            for parent in IMPLIES.get(s, []):
                if parent not in found:
                    found.append(parent)
    order = list(SKILLS)
    return sorted(set(found), key=order.index)


def skills_in(text: str) -> set[str]:
    return set(extract_skills(text))


def skill_positions(text: str) -> list[str]:
    """Skills in the order they appear in the text (no implied skills)."""
    allowed = set(extract_skills(text, with_implied=False))
    first: dict[str, int] = {}
    for canonical, pat in _patterns():
        if canonical in allowed and (m := pat.search(text.lower())):
            first[canonical] = m.start()
    if "Spark" in allowed and "Spark" not in first and (m := _SPARK_BARE.search(text)):
        first["Spark"] = m.start()
    return sorted(first, key=first.get)
