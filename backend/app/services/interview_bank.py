"""Curated interview questions. Technical questions carry key points (regex alternatives) so answers can be
checked for coverage without an LLM. Behavioural/HR questions are scored on STAR structure."""

Q = dict  # {"text", "category", "skill"?, "key_points": [[label, regex], ...]}

HR = [
    Q(text="Tell me about yourself.", category="hr"),
    Q(text="Why do you want to join {company}?", category="hr", needs_company=True),
    Q(text="Why should we hire you for this {role} role?", category="hr"),
    Q(text="What is your current notice period, and can you join earlier if needed?", category="hr"),
    Q(text="What are your salary expectations (in LPA), and how did you arrive at that number?", category="hr"),
    Q(text="Are you open to relocating or working from the office/hybrid?", category="hr"),
    Q(text="Where do you see yourself in three years?", category="hr"),
]

BEHAVIOURAL = [
    Q(text="Describe a project you're proud of. What was your specific contribution and its result?",
      category="behavioural"),
    Q(text="Tell me about a time you faced a tight deadline. What did you do?", category="behavioural"),
    Q(text="Describe a disagreement with a teammate and how you resolved it.", category="behavioural"),
    Q(text="Tell me about a mistake you made and what you learned from it.", category="behavioural"),
    Q(text="Describe a time you had to learn a new tool or skill quickly.", category="behavioural"),
]

TECHNICAL: dict[str, list[Q]] = {
    "Python": [
        Q(text="What is the difference between a list and a tuple in Python, and when would you use each?",
          key_points=[["mutability", r"mutable|immutable|can't be changed|cannot be changed"],
                      ["hashable / dict keys", r"hash|dictionary key|dict key|set"],
                      ["use case", r"fixed|constant|record|coordinates|return multiple"]]),
        Q(text="Explain Python decorators with an example.",
          key_points=[["wraps a function", r"wrap|wrapper|takes a function|returns a function"],
                      ["@ syntax", r"@"], ["use case", r"logging|timing|auth|cache|retry"]]),
        Q(text="What are generators and why are they memory-efficient?",
          key_points=[["yield", r"yield"], ["lazy evaluation", r"lazy|one at a time|on demand|iterat"],
                      ["memory", r"memory|don't store|do not store|large"]]),
    ],
    "SQL": [
        Q(text="What is the difference between WHERE and HAVING?",
          key_points=[["WHERE filters rows before grouping", r"before (?:the )?group|individual rows|row level"],
                      ["HAVING filters after grouping", r"after (?:the )?group|aggregat|group by"]]),
        Q(text="Explain INNER, LEFT and FULL OUTER joins.",
          key_points=[["inner = matching rows", r"inner.{0,40}(?:match|both|common)"],
                      ["left keeps all left rows", r"left.{0,40}(?:all|every).{0,20}left"],
                      ["full keeps both sides", r"full.{0,40}(?:both|all)"], ["NULLs", r"null"]]),
        Q(text="How would you find the second-highest salary in a table?",
          key_points=[["subquery / window", r"subquery|max\s*\(|dense_rank|rank\s*\(|row_number|offset|limit"],
                      ["ties / duplicates", r"tie|duplicate|distinct|dense"]]),
    ],
    "Java": [
        Q(text="What is the difference between an interface and an abstract class in Java?",
          key_points=[["multiple inheritance", r"multiple|implement more than one|several interfaces"],
                      ["state / constructors", r"state|field|constructor|instance variable"],
                      ["default methods", r"default method|java 8"]]),
        Q(text="Explain how HashMap works internally.",
          key_points=[["hashing to buckets", r"bucket|hash ?code|hashcode"], ["collisions", r"collision|linked list|tree"],
                      ["equals/hashCode contract", r"equals"]]),
    ],
    "JavaScript": [
        Q(text="Explain closures in JavaScript with an example.",
          key_points=[["function remembers outer scope", r"outer|lexical|scope|remember"],
                      ["use case", r"private|counter|callback|module|factory"]]),
        Q(text="What is the event loop?",
          key_points=[["single-threaded", r"single[- ]thread"], ["call stack", r"call stack|stack"],
                      ["task / microtask queue", r"queue|microtask|callback"]]),
    ],
    "React": [
        Q(text="What problem do React hooks like useEffect solve, and what is the dependency array for?",
          key_points=[["side effects", r"side effect|fetch|subscription|api call"],
                      ["dependency array", r"dependenc|re-?run|when .{0,20}change"], ["cleanup", r"cleanup|clean up|return"]]),
        Q(text="Why do list items in React need a key?",
          key_points=[["identity across renders", r"identif|track|which item|reconcil"],
                      ["avoid index keys", r"index|stable|unique"]]),
    ],
    "Data Analysis": [
        Q(text="How do you handle missing values in a dataset?",
          key_points=[["understand why missing", r"why|pattern|random|mcar|mnar"],
                      ["drop vs impute", r"drop|remove|delete"], ["impute", r"impute|mean|median|mode|fill"]]),
        Q(text="Walk me through how you'd analyse a sudden 20% drop in weekly sales.",
          key_points=[["verify data first", r"data (?:quality|issue|error)|tracking|verify|check the data"],
                      ["segment", r"segment|region|product|channel|break ?down"],
                      ["external factors", r"season|holiday|competitor|price|festival"]]),
    ],
    "Excel": [
        Q(text="When would you use XLOOKUP/VLOOKUP versus INDEX-MATCH?",
          key_points=[["lookup direction / left lookup", r"left|direction|column order"],
                      ["exact match", r"exact|false|0"], ["performance / robustness", r"insert|robust|faster|performance"]]),
        Q(text="How would you summarise 50,000 rows of sales data by region and month?",
          key_points=[["pivot table", r"pivot"], ["dates / grouping", r"month|group|date"]]),
    ],
    "Power BI": [
        Q(text="What is the difference between a calculated column and a measure in Power BI?",
          key_points=[["row context vs filter context", r"row|context|filter"], ["storage / when computed", r"stored|query time|on the fly|refresh"]]),
    ],
    "Machine Learning": [
        Q(text="What is overfitting and how do you prevent it?",
          key_points=[["train vs test gap", r"training.{0,30}(?:well|good)|unseen|test|generali"],
                      ["remedies", r"regulari|cross[- ]validation|more data|dropout|simpler|pruning|early stopping"]]),
        Q(text="How would you evaluate a classifier on an imbalanced dataset?",
          key_points=[["accuracy misleads", r"accuracy"], ["precision/recall/F1", r"precision|recall|f1"],
                      ["ROC/PR AUC", r"auc|roc|pr curve"], ["resampling", r"smote|oversampl|undersampl|class weight"]]),
    ],
    "DSA": [
        Q(text="How would you detect a cycle in a linked list?",
          key_points=[["two pointers", r"two pointers|fast.{0,20}slow|floyd|tortoise"], ["O(1) space", r"o\(1\)|constant space"]]),
        Q(text="When would you use a hash map versus a sorted array?",
          key_points=[["O(1) lookup", r"o\(1\)|constant"], ["ordering / range queries", r"order|sorted|range|binary search"]]),
    ],
    "System Design": [
        Q(text="How would you design a URL shortener?",
          key_points=[["ID generation", r"hash|base ?62|counter|unique id"], ["storage", r"database|key[- ]value|table"],
                      ["caching", r"cache|redis"], ["scale reads", r"read[- ]heavy|replica|cdn|load balanc"]]),
    ],
    "Docker": [
        Q(text="What is the difference between a Docker image and a container?",
          key_points=[["image = template", r"template|blueprint|read[- ]only|snapshot"], ["container = running instance", r"running|instance"]]),
    ],
    "Thermodynamics": [
        Q(text="Explain the difference between the first and second laws of thermodynamics with an engineering example.",
          key_points=[["energy conservation", r"conserv|energy (?:is )?neither"], ["entropy / direction", r"entropy|direction|irrevers"],
                      ["example", r"engine|turbine|refrigerat|heat pump|boiler"]]),
    ],
    "Heat Transfer": [
        Q(text="Compare conduction, convection and radiation, and name where each dominates in a heat exchanger.",
          key_points=[["conduction through wall", r"conduct.{0,40}(?:wall|solid|tube)"], ["convection with fluids", r"convect.{0,40}(?:fluid|flow)"],
                      ["radiation", r"radiat"]]),
    ],
    "Fluid Mechanics": [
        Q(text="What does the Reynolds number tell you, and why does it matter in pipe design?",
          key_points=[["inertia vs viscous", r"inertia|viscous|viscosity"], ["laminar / turbulent", r"laminar|turbulent"],
                      ["pressure drop / friction", r"pressure drop|friction|head loss|moody"]]),
    ],
    "SolidWorks": [
        Q(text="How do you make a SolidWorks model easy to modify later (design intent)?",
          key_points=[["fully defined sketches", r"fully defined|constraint|relation"], ["parametric / equations", r"parametric|equation|global variable|dimension"],
                      ["feature order", r"feature (?:order|tree)|history"]]),
    ],
    "GD&T": [
        Q(text="What is the difference between position tolerance and plus/minus tolerancing?",
          key_points=[["cylindrical zone", r"cylind|circular zone|round zone"], ["datums", r"datum"], ["MMC bonus", r"mmc|bonus|material condition"]]),
    ],
    "Manufacturing": [
        Q(text="A part fails inspection repeatedly on one dimension. How do you find the root cause?",
          key_points=[["data / measurement check", r"measur|gauge|msa|calibrat"], ["root-cause tool", r"5 why|fishbone|ishikawa|root cause"],
                      ["process capability", r"cpk|capability|spc|control chart"]]),
    ],
    "Accounting": [
        Q(text="Explain input tax credit under GST with an example.",
          key_points=[["credit for GST paid on inputs", r"input|purchase|paid on"], ["offset against output tax", r"output|offset|set off|liability"]]),
    ],
    "Sales": [
        Q(text="How would you handle a client who says your product is too expensive?",
          key_points=[["understand the objection", r"understand|ask|why|budget"], ["value not price", r"value|roi|benefit|cost of"],
                      ["options", r"plan|discount|option|trial|phased"]]),
    ],
}

# skills that should borrow another skill's questions
ALIASES = {"Pandas": "Python", "NumPy": "Python", "Django": "Python", "Flask": "Python", "FastAPI": "Python",
           "MySQL": "SQL", "PostgreSQL": "SQL", "Spring Boot": "Java", "Spring": "Java", "TypeScript": "JavaScript",
           "Next.js": "React", "Node.js": "JavaScript", "Tableau": "Data Analysis", "Statistics": "Data Analysis",
           "Data Visualization": "Data Analysis", "Deep Learning": "Machine Learning", "NLP": "Machine Learning",
           "Kubernetes": "Docker", "CATIA": "SolidWorks", "Creo": "SolidWorks", "AutoCAD": "SolidWorks",
           "ANSYS": "Heat Transfer", "CFD": "Fluid Mechanics", "Piping": "Fluid Mechanics", "HVAC": "Heat Transfer",
           "Quality Control": "Manufacturing", "Lean / Six Sigma": "Manufacturing", "GST": "Accounting",
           "Tally": "Accounting", "CRM": "Sales"}
