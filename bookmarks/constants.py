# Standard Library
import os
import pathlib

KNOWLEDGE_BASE_PATH = "data/wkerr-kg"
RESEARCH_PAPERS_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-papers")
RESEARCH_MARKDOWN_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-md")
RESEARCH_NOTES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-notes")


TWITTER_MEDIA_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/media")
TWITTER_JSON_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/json")
TWITTER_NOTES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/notes")

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")  # Get from environment variable
TWITTER_RAW_PATH = pathlib.Path("/tmp/twitter/raw")

WEB_PAGE_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-pages")
WEB_MARKDOWN_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-markdown")
WEB_READABILITY_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-readability")
WEB_READABILITY_HTML_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-readability-html")
WEB_SUMMARY_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-notes")

FOLDER_STRUCTURE = [
    "AI/DeepLearning/Architectures",
    "AI/DeepLearning/Agents",
    "AI/DeepLearning/GenerativeAI",
    "AI/DeepLearning/GameAI",
    "AI/DeepLearning/ReinforcementLearning",
    "AI/DeepLearning/Safety",
    "AI/DeepLearning/ExplainableAI",
    "AI/Ethics",
    "AI/MachineLearning/Applications",
    "AI/MachineLearning/ClassicalAlgorithms",
    "AI/MachineLearning/Engineering",
    "AI/RecommenderSystems",
    "Personal/Finance",
    "Personal/Health",
    "Personal/Politics",
    "Personal/Entertainment",
    "Professional/Productivity",
    "Professional/SoftwareEngineering",
    "Research/DataScience",
    "Research/Science",
    "Research/Technology",
]
