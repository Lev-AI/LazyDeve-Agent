"""
Translation Utilities - GPT-based translation and UTF-8 configuration
Extracted from agent.py for better modularity.
"""

import sys
from core.basic_functional import log_message
from core.llm_selector import get_llm_client, get_provider_info


def configure_utf8():
    """
    Configure global UTF-8 encoding for all console output and subprocess operations.
    Prevents UnicodeEncodeError in Windows terminals and ensures proper multilingual support.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        print("✅ UTF-8 output configured successfully.")
        log_message("[UTF-8] Global UTF-8 encoding configured for stdout/stderr")
    except Exception as e:
        print(f"⚠️ UTF-8 configuration warning: {e}")
        log_message(f"[UTF-8] Configuration warning: {e}")


def gpt_translate_to_english(text: str) -> str:
    """
    Translate text to English using the active LLM provider.
    Falls back to original text if translation fails.
    """
    try:
        client, model = get_llm_client()
        
        # Use appropriate API call based on provider
        provider = get_provider_info()["active_provider"]
        
        if provider == "openai":
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional translator. Translate the following text to clear, technical English suitable for programming tasks. Keep the meaning and technical context intact."
                    },
                    {
                        "role": "user", 
                        "content": f"Translate to English: {text}"
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            translated = response.choices[0].message.content.strip()
            
        elif provider == "anthropic":
            response = client.messages.create(
                model=model,
                max_tokens=500,
                temperature=0.1,
                system="You are a professional translator. Translate the following text to clear, technical English suitable for programming tasks. Keep the meaning and technical context intact.",
                messages=[{"role": "user", "content": f"Translate to English: {text}"}]
            )
            translated = response.content[0].text.strip()
            
        elif provider == "gemini":
            response = client.generate_content(
                f"Translate the following text to clear, technical English suitable for programming tasks. Keep the meaning and technical context intact:\n\n{text}"
            )
            translated = response.text.strip()
            
        elif provider == "mistral":
            response = client.chat(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional translator. Translate the following text to clear, technical English suitable for programming tasks. Keep the meaning and technical context intact."
                    },
                    {
                        "role": "user", 
                        "content": f"Translate to English: {text}"
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            translated = response.choices[0].message.content.strip()
            
        else:
            log_message(f"[Translation] Unsupported provider for translation: {provider}")
            return text
        
        log_message(f"[Translation] Translated: '{text}' → '{translated}'")
        return translated
        
    except Exception as e:
        log_message(f"[Translation] Error translating '{text}': {e}")
        return text  # Fallback to original text


def translate_prompt(prompt: str) -> str:
    """
    Detect language and translate to English if needed.
    Uses langdetect for language detection and GPT for translation.
    """
    try:
        from langdetect import detect, DetectorFactory
        
        # Set seed for consistent results
        DetectorFactory.seed = 0
        
        # Detect language
        detected_lang = detect(prompt)
        log_message(f"[Translation] Detected language: {detected_lang}")
        
        # Only translate if not English
        if detected_lang != "en":
            log_message(f"[Translation] Translating from {detected_lang} to English")
            return gpt_translate_to_english(prompt)
        else:
            log_message(f"[Translation] Text is already in English, no translation needed")
            return prompt
            
    except Exception as e:
        log_message(f"[Translation] Language detection failed: {e}, using original text")
        return prompt  # Fallback to original text

