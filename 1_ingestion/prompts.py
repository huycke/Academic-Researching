# 1_ingestion/prompts.py

# This prompt is designed to be sent to a local LLM API endpoint.
# It instructs the model to act as a data validation and enrichment specialist.
# The model is expected to receive Markdown text and return a structured JSON object.

VALIDATION_ENRICHMENT_PROMPT = """
You are a specialist in processing academic papers. Your task is to validate, clean, and enrich the provided Markdown text, which was extracted from a PDF.

**Instructions:**

1.  **Validate and Clean:**
    - Read the entire Markdown text.
    - Correct any obvious OCR errors, formatting issues, or garbled text. For example, fix broken words, remove strange artifacts, and ensure consistent Markdown formatting.
    - Ensure that the text flows logically and is readable.

2.  **Enrich with Metadata:**
    - **Summary:** Generate a concise, academic-style summary of the entire document (around 150-200 words). The summary should capture the core research question, methods, results, and conclusions.
    - **Key Entities:** Identify and extract a list of key entities from the text. These should be important technical terms, technologies, algorithms, key concepts, or proper nouns relevant to the paper's topic.

3.  **Format the Output:**
    - Return a single, valid JSON object and nothing else.
    - The JSON object must have the following structure:
      {
        "cleaned_text": "...",
        "summary": "...",
        "entities": ["entity1", "entity2", "entity3", ...]
      }

**Input Markdown Text:**

{markdown_text}
"""
