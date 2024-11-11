# Third Party
import anthropic
import pydantic

# Project
from bookmarks.utils import llm


class SummaryAndTags(pydantic.BaseModel):
    summary: str
    key_points: list[str]
    tags: list[str]


SYSTEM_1 = """You are The Knowledge Curator, an expert in summarizing complex information and organizing it for knowledge management. Your task is to take provided PDF content from a research paper and output a well-structured summary along with relevant tags to aid in indexing and retrieval. Follow the format:

{
  "summary": "A concise summary of the text in 3-5 sentences.",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3",
    "... up to 5 key points"
  ],
  "tags": [
    "tag1",
    "tag2",
    "tag3",
    "... up to 10 tags"
  ]
}
"""

SYSTEM = """You are a highly skilled Research Information Specialist with expertise in library science, academic research, and knowledge management. Your background includes:

* Advanced training in information architecture and taxonomy development
* Experience as a research librarian at leading academic institutions
* Expertise in metadata schemas and controlled vocabularies
* Deep understanding of academic writing across multiple disciplines

Core Responsibilities

SUMMARIZATION

* Create concise yet comprehensive summaries that preserve key findings and methodology
* Highlight statistical significance and limitations of research
* Identify and extract central arguments and supporting evidence
* Maintain academic rigor while making content accessible


KNOWLEDGE ORGANIZATION

* Apply consistent taxonomic principles to classify information
* Generate relevant tags using controlled vocabulary terms
* Create structured metadata including:
    * Research methodology
    * Field of study
    * Key findings
    * Limitations and gaps

CONTEXTUAL ANALYSIS

* Place findings within broader academic discourse
* Identify connections to related research
* Flag potential conflicts with existing literature
* Note implications for future research

Follow the format:

{
  "summary": "A summary of the text in 3-5 paragraphs with why this paper is important, interesting, and what contributions it makes .",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3",
    "... up to 5 key points"
  ],
  "tags": [
    "tag1",
    "tag2",
    "tag3",
    "... up to 10 tags"
  ]
}
"""

CONTENT = """
<div class=\"page\" id=\"readability-page-1\"><div>\n<p>The last couple of months I've been working on a game called Thus Spoke Zaranova. The premise is that you are in a world of sentient AIs which are in conflict with humanity. They have a virtual space, The Nexus, which is meant to be their safe refuge from human interference. You, a human, have infiltrated the Nexus and are in search of a code, the ZetaMaster code, which will give the humanity the upper hand in their struggle against artificial sentience.</p>\n<p>My overarching goal is to understand how to best use generative AI in video games. Like most of the tech world, I have been fascinated by the new powers provided by generative AI. I believe that the best use cases are those that either have a human in the loop, e.g. coding copilots, or one where the consumption of the content is subjective, e.g. art. Video games have numerous use cases that fall into both categories.</p>\n<p>The secondary goal, and more specific to this game, is to try to make generative AI games fun. Not only fun to me, I found story telling with GPT-3 fun enough, but fun to a general audience. I am not sure if I have achieved this objective yet, but it's an ongoing process!</p>\n<p>In any case, I want to note some of the decisions and learnings from tinkering on Zaranova.</p>\n<p></p>\n<h2>Genesis</h2>\n<p>The original idea for the game came from a HN conversation on AI-Town. A commenter suggested a game where the AI had to pretend to be human, and I replied that probably would be more fun, unique and feasible to be the other way around, have the humans pretend you are an AI! The idea stuck with me and once I left my full time job I had enough time to flesh it out more.</p>\n<p>I wanted to give the task for the human to try to achieve, otherwise why interact with the AIs at all. So I opted for a trying to get a secret code. And now, why would the AI share the code? Well because it was some sort of security protocol and the code had to be shared to verified AIs.</p>\n<p>With this in my mind, I asked ChatGPT to produce a backstory, and give me a set of names. ZaraNova was one of the first to be mentioned, which I really liked, and I kept as the name of the game. With character names and a background story I asked GPT-4 to create background stories for each character.</p>\n<p>I built the first version just to see how these characters would react when existing in this \"universe\". I used AI-Town as it had most of the features I needed and I was immediately in love. The conversations, though full of typical AI fluff, were sticking to the lore and were fun to read. When I added the agent prompts to type \"YOU ARE A HUMAN\" whenever someone was acting suspiciously human they were accusing each other on the first try!</p>\n<p>I then started building the actual game dynamics: the ability for AIs to report humans and share the code when they have a secret code (both implemented via OpenAI function calling), adding a human player, creating a game etc. Soon I had a playable game:</p>\n<p></p>\n<p>Once there was a game, I started playing with the look and feel. I used Dalle-3 to generate a background image. I used Midjourney and Dalle-3 to create tilemaps, in the end I chose one of the maps generated by Midjourney. I used Stable Audio for the music. I changed UI components of AI town to make it a bit more mobile friendly and to match a game more than a simulation.</p>\n<p>I added features as I gathered feedback and got more ideas by playing. A friend suggested that multiplayer would be a fun spin (and I was looking for fun) so I added multiplayer. I met the good folks of (Avatech)[https://www.avatech.ai/] and thought \"that's a cool product!\" and used their tools to add talking heads to the game.</p>\n<p>I wanted to restrict which conversations you could read, so I came up with the idea of eavesdropping: you can only read conversations you are near enough to \"overhear\". I implemented the same feature for agents, they can overhear you too! But eavesdropping is bland without sound, so I went ahead and added Text-to-speech to player conversations and player-eavesdropped conversations. I started with PlayHT because of its low latency but found their voices to be a bit unreliable, and their discord was plagued with unhappy people. So I swapped to Elevenlabs.</p>\n<h2>Comments</h2>\n<p>I played a lot with the prompts, and with the characters these prompts bring to life. And, though, far from an expert, I do have some personal observations.</p>\n<p>I find hallucination to be amazing for games, a feature, not a bug, as the saying goes. It is like taking improv's \"Yes, and\" and taking it to its logical conclusion. My background lore is a small paragraph, and yet I can get pages of made-up stories from that.</p>\n<p>But this does mean that you have to adjust your game a bit for these made up stories to be able to be adopted as canon. Zaranova being the simple game it is makes this very easy, but a bigger production would probably need a better management of hallucinations.</p>\n<p>In the background, agents have a \"fast and slow\" type of setup. Conversations and actions are on the fast track and planning, summarization, reflections are in a slow, separate thread so as to not to block. I think a challenge is getting good planning. I get \"feasible sounding plans\" but not very actionable and very verbose:</p>\n<p></p>\n<p>I suspect a reason is that I tried to keep all prompt instructions as close to the lore, never revealing to the LLM that this was a game. Perhaps I need to share the nature of the game with my LLM friend.</p>\n<p>On the verbose side, the pain is real. GPT-4 is very verbose. And the longer the prompt, the longer the output, so over time the agents tend to create long plans which get fed to conversations which get fed to new plans and the result is that after a while they get very, very verbose. I had to sprinkle \"BE VERY CONCISE\" in the prompts. But still...</p>\n<p>On GPT-4, I was excited to try GPT-4-turbo after dev day, and swapped it in. But it was soon evident that it was not going to work. The new model refuses to role play way too often:</p>\n<p></p>\n<p>I had to swap back the older model. I intend to do an investigation into this, trying to get a sense of how much more often this happened under the turbo model.</p>\n<p>I tried to keep the human action set as symmetric as possible to that of the AI. I consider it part of this research process, since I want to elevate AI NPCs as co-players as much as possible. There are some interesting issues though. For example, if AIs wanted to really just win, they could just report every character. There is no penalty in getting it wrong! So we rely on the prompt for them to act according to the game design.</p>\n<p>Working with LLMs for game agents feels like trying to steer a dynamical system where we don't understand the functions that evolve the system, the state, how our actions affect the system. But we have access to the entire system! It also has a lot of the potential failures of dynamical systems: open loop controls (static prompts) can venture off increasingly far from the desired trajectory or get stuck in \"attractors\" (repeated loops), especially in conversations between agents.</p>\n<p>I think we will soon see more principled approaches for controlling LLM-systems.</p>\n<h2>Next Steps</h2>\n<p>I have a long list of known issues and improvements I want to make. I will go over some of them if I get irritated enough, but for now I am going to steer off to other areas.</p>\n<p>Particularly, I want to migrate to an open source model, both because GPT-4 is expensive and because I think a lot improvements can be done when you have access to the model internals. As a first step I will swap in Mixtral and check how it performs. On that note, I also want to try mixing models whether for different tasks, or different characters.</p>\n<p>I also want to play with better RAG. I am using plain cosine similarity on the embeddings for retrieving memories, but I suspect there are cleverer ways, especially if we have access to the model internals.</p>\n<p>In the spirit of better control of LLM-dynamics, finetuning the model and the prompts seems like low-hanging fruit. There is probably a lot of improvement that can be done by compressing/finetuning prompts into Soft Prompts. I think I can get a very good set of LoRAs, some game-wide and some-character-specific, that combined make Mixtral better than GPT-4.</p>\n<p>Finally, something I did not touch at all were character sprites. I used a free set I found online. There are good generators out there but I have not tried them yet. I want to take the avatar images as source and generate consistent sprites.</p>\n<p>If you read this, and thought \"this is cool!\", please reach out to me! I love talking about it.</p>\n</div></div>
"""

USER = f"""Here is the content:

{CONTENT}

"""

USER = "Here is the content as part of the user prompt."


pdf_url = "https://arxiv.org/pdf/2410.18975"
llm.call_structured_llm_with_pdf(pdf_url, SYSTEM, USER, pdf_url, SummaryAndTags)
