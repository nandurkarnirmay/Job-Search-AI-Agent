"""Curated career data: role families with typical progression, core skills and adjacent moves, plus free
learning resources and project ideas per skill. 'Typical years' are rough guides for the Indian market, shown
to users as such. Resource links point at stable, official or long-standing free pages."""

Family = dict

FAMILIES: dict[str, Family] = {
    "software": dict(
        match=r"software|sde|developer|programmer|full ?stack|java dev|python dev|engineer.*(software|backend)",
        ladder=[("Software Engineer / SDE-1", "0–2"), ("SDE-2", "2–5"), ("Senior Software Engineer", "5–8"),
                ("Staff Engineer / Engineering Manager", "8+")],
        core=["DSA", "OOP", "SQL", "Git", "REST APIs", "System Design", "Unit Testing", "Docker"],
        adjacent=["Backend Developer", "DevOps / Cloud Engineer", "Data Engineer"]),
    "backend": dict(
        match=r"backend|back-end|api developer|node(\.js)? developer|django|spring",
        ladder=[("Backend Developer", "0–2"), ("Backend Engineer II", "2–5"), ("Senior Backend Engineer", "5–8"),
                ("Tech Lead / Architect", "8+")],
        core=["Python", "Java", "SQL", "PostgreSQL", "REST APIs", "Docker", "Redis", "System Design", "Git"],
        adjacent=["Software Engineer", "DevOps / Cloud Engineer", "Data Engineer"]),
    "frontend": dict(
        match=r"front ?end|react|ui developer|web developer|angular",
        ladder=[("Frontend Developer", "0–2"), ("Frontend Engineer II", "2–5"), ("Senior Frontend Engineer", "5–8"),
                ("Frontend Lead / Architect", "8+")],
        core=["HTML", "CSS", "JavaScript", "TypeScript", "React", "REST APIs", "Git", "Unit Testing"],
        adjacent=["Full-stack Developer", "UI/UX Designer", "Mobile Developer"]),
    "data_analyst": dict(
        match=r"data analyst|business analyst|analytics|mis|bi developer|reporting analyst|power bi",
        ladder=[("Data / Business Analyst", "0–2"), ("Senior Data Analyst", "2–5"), ("Analytics Lead", "5–8"),
                ("Analytics Manager / Head of Analytics", "8+")],
        core=["SQL", "Excel", "Python", "Pandas", "Statistics", "Power BI", "Tableau", "Data Visualization"],
        adjacent=["Data Scientist", "Data Engineer", "Product Analyst"]),
    "data_scientist": dict(
        match=r"data scien|machine learning|ml engineer|ai engineer|deep learning|nlp|computer vision|gen ?ai",
        ladder=[("Data Scientist / ML Engineer", "0–2"), ("Data Scientist II", "2–5"), ("Senior Data Scientist", "5–8"),
                ("Lead / Principal Data Scientist", "8+")],
        core=["Python", "Statistics", "Machine Learning", "Pandas", "SQL", "scikit-learn", "Deep Learning",
              "Generative AI", "Git"],
        adjacent=["Data Analyst", "Data Engineer", "MLOps Engineer"]),
    "data_engineer": dict(
        match=r"data engineer|etl|big data|spark|pipeline engineer",
        ladder=[("Data Engineer", "0–2"), ("Data Engineer II", "2–5"), ("Senior Data Engineer", "5–8"),
                ("Data Architect / Lead", "8+")],
        core=["SQL", "Python", "ETL", "Spark", "Airflow", "AWS", "Docker", "Kafka"],
        adjacent=["Backend Developer", "Data Scientist", "DevOps / Cloud Engineer"]),
    "devops": dict(
        match=r"devops|cloud|sre|site reliability|platform engineer|infrastructure",
        ladder=[("DevOps / Cloud Engineer", "0–2"), ("DevOps Engineer II", "2–5"), ("Senior SRE / Cloud Engineer", "5–8"),
                ("Platform / Infra Lead", "8+")],
        core=["Linux", "Bash", "Git", "Docker", "Kubernetes", "AWS", "Terraform", "CI/CD"],
        adjacent=["Backend Developer", "Data Engineer", "Security Engineer"]),
    "mechanical_design": dict(
        match=r"design engineer|mechanical|cad|product design|get|graduate engineer trainee|r&d engineer",
        ladder=[("Graduate Engineer Trainee / Design Engineer", "0–2"), ("Design Engineer", "2–5"),
                ("Senior Design Engineer", "5–8"), ("Lead Engineer / Engineering Manager", "8+")],
        core=["AutoCAD", "SolidWorks", "GD&T", "Creo", "FEA", "ANSYS", "Manufacturing", "MATLAB"],
        adjacent=["CAE / Simulation Engineer", "Manufacturing Engineer", "Quality Engineer"]),
    "thermal_cae": dict(
        match=r"thermal|cfd|cae|simulation|hvac|piping|heat transfer",
        ladder=[("CAE / Thermal Engineer", "0–2"), ("CAE Engineer II", "2–5"), ("Senior CAE / Thermal Engineer", "5–8"),
                ("CAE Lead / Technical Specialist", "8+")],
        core=["Thermodynamics", "Heat Transfer", "Fluid Mechanics", "CFD", "ANSYS", "MATLAB", "Python", "Piping"],
        adjacent=["Design Engineer", "Energy / Process Engineer", "Data Scientist (engineering data)"]),
    "manufacturing": dict(
        match=r"manufacturing|production|process engineer|plant|operations engineer|industrial engineer",
        ladder=[("Production / Process Engineer", "0–2"), ("Manufacturing Engineer", "2–5"),
                ("Senior Manufacturing Engineer / Shift Lead", "5–8"), ("Plant / Operations Manager", "8+")],
        core=["Manufacturing", "Lean / Six Sigma", "Quality Control", "AutoCAD", "SAP", "Excel", "PLC / SCADA"],
        adjacent=["Quality Engineer", "Supply Chain Analyst", "Design Engineer"]),
    "quality": dict(
        match=r"quality|qa engineer(?!.*software)|qc|inspection|reliability engineer",
        ladder=[("Quality Engineer", "0–2"), ("Quality Engineer II", "2–5"), ("Senior Quality Engineer", "5–8"),
                ("Quality Manager", "8+")],
        core=["Quality Control", "Lean / Six Sigma", "GD&T", "Statistics", "Manufacturing", "Excel"],
        adjacent=["Manufacturing Engineer", "Supplier Quality Engineer", "Process Engineer"]),
    "finance": dict(
        match=r"account|finance|financial analyst|ca|audit|tax|gst|bank",
        ladder=[("Accounts / Finance Executive", "0–2"), ("Financial Analyst", "2–5"), ("Finance Manager", "5–8"),
                ("Finance Controller / Head of Finance", "8+")],
        core=["Accounting", "Excel", "GST", "Tally", "SAP", "Financial Analysis", "Power BI"],
        adjacent=["Business Analyst", "FP&A Analyst", "Audit Associate"]),
    "sales_marketing": dict(
        match=r"sales|business development|bde|marketing|seo|growth|account executive",
        ladder=[("Sales / Marketing Executive", "0–2"), ("Senior Executive / Specialist", "2–5"), ("Manager", "5–8"),
                ("Head of Sales / Marketing", "8+")],
        core=["Sales", "Digital Marketing", "CRM", "Excel", "Communication", "Data Analysis"],
        adjacent=["Account Manager", "Product Marketing", "Customer Success"]),
}

# skill -> (resource title, url); stable official/free starting points
RESOURCES: dict[str, list[tuple[str, str]]] = {
    "Python": [("Official Python tutorial", "https://docs.python.org/3/tutorial/")],
    "SQL": [("SQLBolt interactive lessons", "https://sqlbolt.com/")],
    "PostgreSQL": [("PostgreSQL tutorial (official docs)", "https://www.postgresql.org/docs/current/tutorial.html")],
    "Excel": [("Microsoft Excel help & learning", "https://support.microsoft.com/excel")],
    "Power BI": [("Microsoft Learn: Power BI", "https://learn.microsoft.com/training/powerplatform/power-bi")],
    "Tableau": [("Tableau free training", "https://www.tableau.com/learn/training")],
    "Pandas": [("pandas getting started", "https://pandas.pydata.org/docs/getting_started/index.html")],
    "Statistics": [("Khan Academy: Statistics & probability", "https://www.khanacademy.org/math/statistics-probability")],
    "Machine Learning": [("Google ML Crash Course", "https://developers.google.com/machine-learning/crash-course")],
    "scikit-learn": [("scikit-learn tutorials", "https://scikit-learn.org/stable/tutorial/index.html")],
    "Deep Learning": [("fast.ai Practical Deep Learning", "https://course.fast.ai/")],
    "Generative AI": [("Hugging Face LLM course", "https://huggingface.co/learn")],
    "Git": [("Pro Git book", "https://git-scm.com/book/en/v2")],
    "Docker": [("Docker getting started", "https://docs.docker.com/get-started/")],
    "Kubernetes": [("Kubernetes basics", "https://kubernetes.io/docs/tutorials/kubernetes-basics/")],
    "AWS": [("AWS Skill Builder (free courses)", "https://skillbuilder.aws/")],
    "Terraform": [("Terraform tutorials", "https://developer.hashicorp.com/terraform/tutorials")],
    "Linux": [("Linux Journey", "https://linuxjourney.com/")],
    "JavaScript": [("The Modern JavaScript Tutorial", "https://javascript.info/")],
    "TypeScript": [("TypeScript handbook", "https://www.typescriptlang.org/docs/handbook/intro.html")],
    "React": [("react.dev: Learn React", "https://react.dev/learn")],
    "HTML": [("MDN: Learn web development", "https://developer.mozilla.org/en-US/docs/Learn")],
    "CSS": [("MDN: Learn web development", "https://developer.mozilla.org/en-US/docs/Learn")],
    "Java": [("dev.java: Learn Java", "https://dev.java/learn/")],
    "Spring Boot": [("Spring guides", "https://spring.io/guides")],
    "DSA": [("LeetCode Explore", "https://leetcode.com/explore/")],
    "System Design": [("System Design Primer", "https://github.com/donnemartin/system-design-primer")],
    "REST APIs": [("MDN: HTTP overview", "https://developer.mozilla.org/en-US/docs/Web/HTTP")],
    "MATLAB": [("MATLAB Onramp (free)", "https://matlabacademy.mathworks.com/")],
    "ANSYS": [("Ansys Innovation Courses (free)", "https://innovationspace.ansys.com/courses/")],
    "Lean / Six Sigma": [("ASQ: Six Sigma resources", "https://asq.org/quality-resources/six-sigma")],
    "Airflow": [("Apache Airflow tutorial", "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html")],
    "Spark": [("Spark quick start", "https://spark.apache.org/docs/latest/quick-start.html")],
}
NPTEL = ("NPTEL (free IIT/IISc courses): search '{skill}'", "https://nptel.ac.in/courses")
CORE_ENGINEERING = {"AutoCAD", "SolidWorks", "GD&T", "Creo", "FEA", "CFD", "Manufacturing", "Thermodynamics",
                    "Heat Transfer", "Fluid Mechanics", "Piping", "Quality Control", "PLC / SCADA", "HVAC",
                    "Accounting", "GST"}

PROJECTS: dict[str, str] = {
    "SQL": "Load a public dataset (e.g. Indian railways or IPL) into PostgreSQL and answer 10 business questions "
           "with joins, window functions and CTEs; publish the queries on GitHub.",
    "Python": "Automate something real: a script that cleans a messy CSV and emails a summary.",
    "Power BI": "Build a sales dashboard with drill-downs from a public retail dataset; publish screenshots + .pbix.",
    "Tableau": "Recreate one dashboard from Tableau Public's gallery with your own dataset.",
    "Machine Learning": "Predict a target on a Kaggle dataset end-to-end: baseline, features, validation, write-up.",
    "Docker": "Containerise one of your projects with a Dockerfile and docker-compose (app + database).",
    "React": "Build a job tracker UI that calls a public API, with loading/error states and tests.",
    "System Design": "Write a 2-page design for a URL shortener or rate limiter: APIs, data model, scaling.",
    "DSA": "Solve 2 problems a day by pattern (arrays, hashing, two pointers, BFS/DFS) for 6 weeks.",
    "SolidWorks": "Model and fully dimension a gearbox or bracket assembly with a drawing sheet using GD&T.",
    "ANSYS": "Run a static structural or thermal analysis of a bracket/heat sink and validate against hand calcs.",
    "CFD": "Simulate pipe flow or a heat sink in Ansys Fluent/OpenFOAM and compare with textbook correlations.",
    "MATLAB": "Write a solver for a heat-conduction or vibration problem and plot results against analytical ones.",
    "Lean / Six Sigma": "Do a DMAIC write-up of a process you know (mess queue, lab workflow) with data.",
    "Excel": "Build a model with lookups, pivot tables and charts that answers a real question (budget, sales).",
}
WEEKS = {"DSA": 6, "System Design": 4, "Machine Learning": 6, "Deep Learning": 6, "Kubernetes": 3, "AWS": 4,
         "React": 4, "Java": 5, "Python": 3, "SQL": 2, "Excel": 2, "Power BI": 2, "Tableau": 2, "SolidWorks": 4,
         "ANSYS": 4, "CFD": 5, "FEA": 4}

# check specific families first: the generic "software" pattern ("developer") would swallow e.g. "React developer"
FAMILIES["software"] = FAMILIES.pop("software")
