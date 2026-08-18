import google.generativeai as genai

from app.config import get_settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        genai.configure(api_key=get_settings().gemini_api_key)
        _configured = True


def generate_dialogue(system_prompt: str, user_message: str, history=None) -> str:
    _ensure_configured()
    model = genai.GenerativeModel(
        model_name=get_settings().gemini_model_id,
        system_instruction=system_prompt,
    )

    # Gemini names the assistant role "model".
    gemini_history = [
        {"role": "user" if turn["speaker"] == "player" else "model",
         "parts": [turn["content"]]}
        for turn in history or []
    ]
    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(user_message, request_options={"timeout": 30})
    return response.text
