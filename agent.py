"""
agent.py — Uses Claude (with tool use) to extract dog info and score cuteness.
Handles captions in Spanish and Catalan.
"""

import logging
import anthropic
from dataclasses import dataclass
from typing import Optional
from scraper import RawPost

logger = logging.getLogger(__name__)
client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "classify_dog_post",
        "description": (
            "Determine if this Instagram post is about a dog available for adoption. "
            "If so, extract structured information. Post may be in Spanish or Catalan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "is_dog_post": {
                    "type": "boolean",
                    "description": "True only if this is a dog available for adoption."
                },
                "name": {"type": "string", "description": "Dog's name if mentioned."},
                "breed": {"type": "string", "description": "Breed or mix. Use 'mestizo' for mixed breed."},
                "size": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "unknown"],
                    "description": "Infer from breed, weight, or explicit mention. Under ~10kg = small."
                },
                "age_years": {
                    "type": "number",
                    "description": "Estimated age in years. Convert months to decimal (6 months = 0.5)."
                },
                "age_label": {
                    "type": "string",
                    "enum": ["puppy", "young", "adult", "senior", "unknown"],
                    "description": "puppy <1yr | young 1-3yr | adult 3-8yr | senior 8yr+"
                },
                "sex": {"type": "string", "enum": ["male", "female", "unknown"]},
                "summary": {
                    "type": "string",
                    "description": "One sentence in English summarising the dog's personality or situation."
                }
            },
            "required": ["is_dog_post"]
        }
    },
    {
        "name": "score_cuteness",
        "description": "Score how photogenic and adoption-appealing the dog looks in the photo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "1 = poor quality or not cute, 10 = extremely photogenic and adorable."
                },
                "reason": {
                    "type": "string",
                    "description": "One short sentence explaining the score."
                }
            },
            "required": ["score", "reason"]
        }
    }
]


@dataclass
class DogRecord:
    shelter: str
    shortcode: str
    post_url: str
    timestamp: str
    image_url: Optional[str]
    is_dog_post: bool
    name: Optional[str] = None
    breed: Optional[str] = None
    size: Optional[str] = None
    age_years: Optional[float] = None
    age_label: Optional[str] = None
    sex: Optional[str] = None
    summary: Optional[str] = None
    cuteness_score: Optional[int] = None
    cuteness_reason: Optional[str] = None


def analyze_post(post: RawPost) -> DogRecord:
    """Run a post through Claude and return a structured DogRecord."""
    content = []
    if post.image_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": post.image_b64}
        })
    content.append({
        "type": "text",
        "text": (
            f"Instagram post from shelter @{post.shelter}.\n\n"
            f"Caption:\n{post.caption[:2000] or '(no caption)'}\n\n"
            "Please call BOTH tools:\n"
            "1. classify_dog_post — extract dog info from caption (and image if present)\n"
            "2. score_cuteness — rate photo appeal (only if image was provided)\n\n"
            "Caption may be in Spanish or Catalan."
        )
    })

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        tools=TOOLS,
        messages=[{"role": "user", "content": content}]
    )

    classify_result = {}
    cuteness_result = {}
    for block in response.content:
        if block.type == "tool_use":
            if block.name == "classify_dog_post":
                classify_result = block.input
            elif block.name == "score_cuteness":
                cuteness_result = block.input

    return DogRecord(
        shelter=post.shelter,
        shortcode=post.shortcode,
        post_url=post.post_url,
        timestamp=post.timestamp,
        image_url=post.image_url,
        is_dog_post=classify_result.get("is_dog_post", False),
        name=classify_result.get("name"),
        breed=classify_result.get("breed"),
        size=classify_result.get("size"),
        age_years=classify_result.get("age_years"),
        age_label=classify_result.get("age_label"),
        sex=classify_result.get("sex"),
        summary=classify_result.get("summary"),
        cuteness_score=cuteness_result.get("score"),
        cuteness_reason=cuteness_result.get("reason"),
    )
