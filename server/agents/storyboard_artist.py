import json
import os
from typing import List

from interfaces.character import CharacterInScene
from interfaces.shot import ShotBriefDescription
from tools.muapi_llm import MuAPILLM
from tools.cinematic_prompt_engine import (
    CinematicPromptEngine,
    CANONICAL_BREATH_FLOAT,
    CANONICAL_SOUND_RULE,
)

_FALLBACK_STORYBOARD = json.dumps({
    "shots": [
        {
            "idx": 0,
            "visual_desc": (
                "Core theme: vertical micro-drama | shocking cold-open | high-tension hook | live-action performance. "
                "A tense corporate office at night. Maya slaps a termination letter directly onto the dark mahogany desk. "
                "Harsh desk lamp lighting casts dramatic shadows. Maya has tired eyes, a slightly wrinkled blazer collar, "
                "and stray hairs catching the rim light. Vertical 9:16 framing, face positioned in upper-middle. "
                "Shot on ARRI Alexa with vintage primes (35mm, f/2.8), shallow focus, natural film grain."
            ),
            "motion_desc": (
                "Punch-in single camera move on Maya as the paper hits the desk. "
                "Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence."
            ),
            "audio_desc": "[Sound Effect] Sharp paper slap echoing in the room, fluorescent light hum. Sound: No score. Production audio only."
        },
        {
            "idx": 1,
            "visual_desc": (
                "Core theme: vertical micro-drama | shot-reverse-shot | intense confrontation | psychological power struggle. "
                "Reverse medium close-up on the senior director sitting opposite. He remains unmoving, fingers steepled, "
                "a faint vein pulsing at his temple and slight stubble along his jaw. Dim practical lamp behind him. "
                "Vertical 9:16 framing isolating his cold, restrained expression. "
                "Shot on ARRI Alexa with vintage primes (35mm, f/2.8), motivated practical light."
            ),
            "motion_desc": (
                "Slow, deliberate push-in toward the director's restrained, calculating face. "
                "Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence."
            ),
            "audio_desc": "[Speaker] Maya (shaky, low voice): You knew about the audit. The entire time. Sound: No score. Production audio only."
        },
        {
            "idx": 2,
            "visual_desc": (
                "Core theme: vertical micro-drama | dramatic cliffhanger | unanswered reveal | restrained ending. "
                "Over-the-shoulder vertical framing. The director slowly slides an unsealed black folder across the desk, "
                "revealing a surveillance photograph underneath. Maya's hand freezes mid-air. "
                "Faint dust motes visible in the desk lamp light. No explosion, no blinding light, just an empty pause. "
                "Shot on ARRI Alexa with vintage primes (35mm, f/2.8), shallow depth of field."
            ),
            "motion_desc": (
                "Subtle downward tilt tracking the black folder sliding across the desk, then locked onto Maya's frozen hand. "
                "Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence."
            ),
            "audio_desc": "[Sound Effect] Paper sliding against wood, sudden silence, heavy held breath. Sound: No score. Production audio only."
        }
    ]
})


class StoryboardArtist:
    """
    Cinematic Storyboard Artist leveraging Mx-Shell's 5-Stage Architecture
    (Zombie Scavenger / ai-shortfilm-prompts) for high-retention micro-dramas.
    """

    def __init__(self):
        self.llm = MuAPILLM()

    async def design_storyboard(
        self,
        script: str,
        characters: List[CharacterInScene],
        user_requirement: str,
    ) -> List[ShotBriefDescription]:
        system_prompt = (
            "You are an elite cinematic storyboard artist and shortfilm director applying the Mx-Shell 5-Stage Prompt Architecture.\n"
            "Your task is to break down a scene script into individual shots optimized for AI video generation (Veo, Omni Flash, Kling, Sora).\n\n"
            "MANDATORY 5-STAGE SHOT STRUCTURE FOR EACH SHOT:\n"
            "1. Core theme: 3-5 tags separated by | (e.g. vertical micro-drama | dialogue confrontation | live-action | no game-CG feel)\n"
            "2. Character & scene: Reference uploaded photo features 100% preserved, no beautification. Detail clothing texture and active scene elements.\n"
            "3. Atmosphere & camera: Specify camera body and lens (e.g. ARRI Alexa + vintage primes 35mm f/2.8). Vertical 9:16 composition with faces in upper-middle.\n"
            "4. Camera rules: MUST include exact sentence: 'Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence.'\n"
            "5. Storyboard flow: Shot 0 = Cold open hook (0-2s survive the swipe), Shot 1+ = Confrontation shot-reverse-shot, Final shot = Cliffhanger cut.\n\n"
            "THE SEVEN HARD RULES (ANTI-SLOP):\n"
            "- Rule 1: BANNED vague praise words ('cinematic', 'epic', 'stunning', 'handsome', '4K', 'HD', 'masterpiece'). Replace with physical details.\n"
            "- Rule 2: Always name camera + lens model (ARRI Alexa, vintage primes 35mm f/2.8).\n"
            "- Rule 3: Always include the full breath-like camera float sentence in motion_desc.\n"
            "- Rule 4: Always include 'Sound: No score. Production audio only.' in audio_desc.\n"
            "- Rule 5: Describe at least 2 imperfection anchors per shot (fabric creases, tired eyes, skin blemish, flickering desk lamp, dust motes).\n"
            "- Rule 6: Restrained ending. No explosion, no blinding light, no melodramatic overacting.\n"
            "- Rule 7: No copyrighted IP names.\n\n"
            "Respond ONLY with a valid JSON object matching the requested schema. No markdown wrapping."
        )

        character_descriptions = "\n".join([
            f"- {c.name}: {c.static_features}. Wearing: {c.dynamic_features}. (Imperfections: subtle skin texture, no beautification)"
            for c in characters if c.is_visible
        ])

        prompt = f"""Design a cinematic vertical micro-drama storyboard for this scene script using the 5-stage architecture.

Scene Script:
{script}

Characters in this scene:
{character_descriptions if character_descriptions else "No named characters"}

Style/Genre requirement: {user_requirement if user_requirement else "Vertical micro-drama, ARRI Alexa realistic live-action"}

Return JSON with this exact structure:
{{
  "shots": [
    {{
      "idx": 0,
      "visual_desc": "Core theme: ... Character & scene: ... Atmosphere: Shot on ARRI Alexa with vintage primes (35mm, f/2.8), 9:16 vertical composition, faces upper-middle. (Include >=2 realistic imperfections)",
      "motion_desc": "Camera move details. Handheld shot. Throughout, maintain an extremely subtle, breath-like camera float to enhance presence.",
      "audio_desc": "[Sound Effect] ... Sound: No score. Production audio only."
    }}
  ]
}}

Rules:
- Create 3-4 shots per scene.
- Shot 0 must be an explosive cold-open hook (0-2s).
- Shot 1+ should be shot-reverse-shot confrontation with rising psychological tension.
- Final shot must be an abrupt, cliffhanger cut."""

        raw = await self.llm.complete(
            prompt, system_prompt=system_prompt, timeout=120, fallback=_FALLBACK_STORYBOARD
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            elif raw.startswith("\n"):
                raw = raw[1:]
            if raw.endswith("```"):
                raw = raw[:-3]

        try:
            data = json.loads(raw.strip())
        except Exception as e:
            print(f"[StoryboardArtist] JSON parse failed ({e}), loading fallback.")
            data = json.loads(_FALLBACK_STORYBOARD)

        shots: List[ShotBriefDescription] = []
        for s in data.get("shots", []):
            # Enforce Anti-slop and 5-stage guards via CinematicPromptEngine
            v_desc = CinematicPromptEngine.sanitize_slop_words(s.get("visual_desc", ""))
            v_desc = CinematicPromptEngine.ensure_imperfections(v_desc, min_count=2)

            m_desc = s.get("motion_desc", "")
            if "breath-like" not in m_desc.lower():
                m_desc = m_desc.rstrip(".") + f". {CANONICAL_BREATH_FLOAT}"

            a_desc = s.get("audio_desc", "")
            if "sound: no score" not in a_desc.lower():
                a_desc = f"{a_desc.rstrip('.')} {CANONICAL_SOUND_RULE}".strip()

            shots.append(ShotBriefDescription(
                idx=s.get("idx", len(shots)),
                visual_desc=v_desc,
                motion_desc=m_desc,
                audio_desc=a_desc,
            ))

        return shots
