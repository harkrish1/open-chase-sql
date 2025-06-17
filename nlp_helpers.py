import re
import os
from transformers import pipeline


def clean_text(text):
    token_classifier = pipeline("token-classification")
    result = token_classifier(text)

    return result