"""Canonical skill taxonomy with aliases for gazetteer-based extraction.

Skills are grouped so the matcher can normalize surface forms such as
"tf" / "tensorflow" / "Tensor Flow" to one canonical skill name.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# Canonical name -> list of aliases (lowercase). Canonical name is always included.
SKILL_GROUPS: Dict[str, List[str]] = {
    # Programming languages
    "python": ["python3", "py"],
    "java": ["java se", "java ee", "j2ee"],
    "javascript": ["js", "ecmascript", "es6", "vanilla js", "java script"],
    "typescript": ["ts", "type script"],
    "c++": ["cpp", "c plus plus"],
    "c#": ["csharp", "c sharp"],
    "c": ["c language"],
    "go": ["golang"],
    "rust": [],
    "ruby": ["ruby on rails", "ror"],
    "php": [],
    "swift": [],
    "kotlin": [],
    "scala": [],
    "r": ["r language", "r programming"],
    "sql": ["structured query language"],
    "bash": ["shell scripting", "unix shell"],
    "html": ["html5"],
    "css": ["css3", "cascading style sheets"],
    # Data / ML / NLP
    "machine learning": ["ml", "supervised learning", "unsupervised learning"],
    "deep learning": ["dl", "neural networks", "neural nets"],
    "natural language processing": ["nlp", "computational linguistics"],
    "computer vision": ["cv", "image processing"],
    "data science": ["data analytics", "data analysis"],
    "data engineering": ["data pipelines", "etl"],
    "statistics": ["statistical analysis", "statistical modelling", "statistical modeling"],
    "feature engineering": [],
    "model evaluation": ["model validation"],
    "recommendation systems": ["recommender systems", "recsys"],
    "time series": ["time-series", "forecasting"],
    "reinforcement learning": ["rl"],
    "generative ai": ["genai", "gen ai", "generative artificial intelligence"],
    "large language models": ["llm", "llms", "large language model"],
    "transformers": ["transformer models", "attention mechanism"],
    "bert": ["bidirectional encoder representations"],
    "gpt": ["generative pre-trained transformer"],
    "named entity recognition": ["ner", "entity extraction"],
    "topic modeling": ["lda", "latent dirichlet allocation"],
    "text classification": ["document classification"],
    "sentiment analysis": ["opinion mining"],
    "information retrieval": ["ir", "search ranking"],
    "word embeddings": ["word2vec", "glove", "fasttext"],
    "tf-idf": ["tfidf", "term frequency inverse document frequency"],
    "cosine similarity": [],
    "scikit-learn": ["sklearn", "scikit learn"],
    "tensorflow": ["tf", "tensor flow"],
    "pytorch": ["torch"],
    "keras": [],
    "huggingface": ["hugging face", "transformers library"],
    "spacy": ["spaCy"],
    "nltk": ["natural language toolkit"],
    "openai api": ["openai", "gpt api"],
    "langchain": [],
    "rag": ["retrieval augmented generation", "retrieval-augmented generation"],
    "vector databases": ["vector db", "faiss", "pinecone", "chromadb", "chroma"],
    "pandas": [],
    "numpy": ["np"],
    "matplotlib": [],
    "seaborn": [],
    "plotly": [],
    "jupyter": ["jupyter notebook", "ipynb"],
    # Web / backend
    "react": ["reactjs", "react.js", "react js"],
    "angular": ["angularjs", "angular.js"],
    "vue": ["vuejs", "vue.js", "vue js"],
    "node.js": ["nodejs", "node js", "node"],
    "express": ["express.js", "expressjs"],
    "django": [],
    "flask": [],
    "fastapi": ["fast api"],
    "spring boot": ["springboot", "spring"],
    "rest api": ["rest apis", "restful", "restful apis", "rest"],
    "graphql": [],
    "microservices": ["microservice architecture"],
    "next.js": ["nextjs"],
    "redux": [],
    # Cloud / DevOps
    "aws": ["amazon web services", "ec2", "s3", "lambda"],
    "azure": ["microsoft azure"],
    "google cloud": ["gcp", "google cloud platform"],
    "docker": ["containers", "containerization"],
    "kubernetes": ["k8s"],
    "ci/cd": ["ci cd", "cicd", "continuous integration", "continuous deployment", "jenkins", "github actions"],
    "terraform": ["iac", "infrastructure as code"],
    "linux": ["unix"],
    "git": ["github", "gitlab", "version control"],
    "mlops": ["ml ops", "model deployment"],
    "airflow": ["apache airflow"],
    "spark": ["apache spark", "pyspark"],
    "hadoop": [],
    "kafka": ["apache kafka"],
    # Databases
    "mysql": [],
    "postgresql": ["postgres"],
    "mongodb": ["mongo"],
    "redis": [],
    "elasticsearch": ["elastic search", "elk"],
    "sqlite": [],
    "oracle": ["oracle db"],
    "snowflake": [],
    "bigquery": ["big query"],
    # Product / process
    "agile": ["scrum", "kanban"],
    "jira": [],
    "unit testing": ["pytest", "junit"],
    "system design": ["distributed systems"],
    # Soft / domain (kept conservative)
    "communication": ["written communication", "verbal communication"],
    "leadership": ["team leadership"],
    "problem solving": ["analytical thinking"],
    # HR / recruiting
    "recruitment": ["recruiting", "talent acquisition", "sourcing"],
    "onboarding": ["new hire orientation"],
    "payroll": ["payroll administration"],
    "employee relations": ["labor relations"],
    "performance management": ["performance reviews", "appraisals"],
    "hris": ["human resource information system", "workday", "bamboo hr"],
    "benefits administration": ["employee benefits", "compensation and benefits"],
    # Finance / accounting / banking
    "accounting": ["bookkeeping", "general ledger"],
    "financial analysis": ["financial reporting", "financial modeling"],
    "budgeting": ["budget management", "forecasting"],
    "excel": ["microsoft excel", "ms excel", "spreadsheets", "ms-excel"],
    "power bi": ["powerbi", "ms power bi"],
    "quickbooks": ["quick books"],
    "sap": ["sap fico"],
    "gaap": ["generally accepted accounting principles"],
    "audit": ["auditing", "internal audit"],
    "reconciliation": ["bank reconciliation", "account reconciliation"],
    "accounts payable": ["ap"],
    "accounts receivable": ["ar"],
    "taxation": ["tax preparation", "tax compliance"],
    # Sales / business development
    "salesforce": ["salesforce.com"],
    "crm": ["customer relationship management"],
    "lead generation": ["prospecting"],
    "account management": ["key account management"],
    "negotiation": ["contract negotiation"],
    "business development": ["biz dev", "partnerships"],
    "customer service": ["client service", "customer support"],
    # Healthcare / fitness
    "patient care": ["patient assessment"],
    "emr": ["electronic medical records", "ehr", "epic", "cerner"],
    "hipaa": ["hipaa compliance"],
    "cpr": ["basic life support", "bls"],
    "nursing": ["registered nurse", "rn"],
    "clinical research": ["clinical trials"],
    "personal training": ["fitness training"],
    # Teaching
    "curriculum development": ["curriculum design", "lesson planning"],
    "classroom management": [],
    "special education": ["iep"],
    # Design / digital / arts
    "adobe photoshop": ["photoshop"],
    "adobe illustrator": ["illustrator"],
    "figma": [],
    "ui/ux": ["ui ux", "user experience", "user interface", "ux design", "ui design"],
    "graphic design": ["visual design"],
    "seo": ["search engine optimization"],
    "content marketing": ["content strategy"],
    "social media": ["social media marketing"],
    # Engineering / construction / aviation / auto
    "autocad": ["auto cad", "cad"],
    "solidworks": ["solid works"],
    "matlab": [],
    "plc": ["programmable logic controller"],
    "project management": ["pmp", "project planning"],
    "quality assurance": ["qa", "quality control"],
    "safety management": ["osha", "ehs"],
    "construction management": ["site supervision"],
    # Legal / advocacy
    "legal research": ["case research"],
    "litigation": ["court filings"],
    "contract management": ["contract review"],
    # Culinary
    "food safety": ["servsafe", "haccp"],
    "inventory management": ["inventory control"],
    "menu planning": ["menu development"],
}

# JD section cues used to split required vs preferred skills.
REQUIRED_SECTION_CUES = (
    "requirements",
    "required skills",
    "required qualifications",
    "must have",
    "must-have",
    "minimum qualifications",
    "what you'll need",
    "what you will need",
    "technical skills",
    "key skills",
    "skills required",
)
BODY_SECTION_CUES = (
    "responsibilities",
    "about the role",
    "about us",
    "what you'll do",
    "what you will do",
    "the role",
    "overview",
    "job summary",
)
PREFERRED_SECTION_CUES = (
    "preferred",
    "nice to have",
    "nice-to-have",
    "good to have",
    "bonus",
    "preferred qualifications",
)


def build_alias_map() -> Tuple[Dict[str, str], List[str]]:
    """Return alias->canonical map and aliases sorted longest-first."""
    alias_to_canonical: Dict[str, str] = {}
    for canonical, aliases in SKILL_GROUPS.items():
        forms = {canonical.lower(), *[a.lower() for a in aliases]}
        for form in forms:
            alias_to_canonical[form] = canonical
    lookup_terms = sorted(alias_to_canonical.keys(), key=len, reverse=True)
    return alias_to_canonical, lookup_terms
