# -*- coding: utf-8 -*-
"""
Emotion detector based on keyword matching + TextBlob sentiment analysis.
Supports Spanish and English.
"""


class EmotionDetector:
    KEYWORDS = {
        "happy": [
            "feliz", "contento", "genial", "excelente", "fantastico",
            "alegre", "perfecto", "estupendo", "happy", "great", "excellent",
            ":)", "😊", "😄", "🎉"
        ],
        "sad": [
            "triste", "mal", "pena", "lamento", "desafortunado",
            "sad", "sorry", "unfortunately", ":(", "😢", "😞"
        ],
        "surprised": [
            "wow", "increible", "sorprendente", "guau", "impresionante",
            "amazing", "incredible", "😮", "😲", "!"
        ],
        "angry": [
            "error", "fallo", "problema", "incorrecto", "imposible",
            "angry", "wrong", "failed", "😠", "😡"
        ],
        "thinking": [
            "hmm", "pensando", "analizo", "veamos", "considerando",
            "thinking", "analyzing", "let me", "🤔"
        ],
    }

    def detect(self, text: str) -> str:
        text_lower = text.lower()
        for emotion, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return emotion
        try:
            from textblob import TextBlob
            polarity = TextBlob(text).sentiment.polarity
            if polarity > 0.3:
                return "happy"
            elif polarity < -0.3:
                return "sad"
            elif "?" in text:
                return "thinking"
        except ImportError:
            pass
        return "neutral"
