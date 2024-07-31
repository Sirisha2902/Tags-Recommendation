**`Text Analysis Interface`**

This project provides a Gradio-based interface for comprehensive text analysis, including entity recognition and keyword extraction. It leverages several NLP techniques and libraries such as SpaCy, TextBlob, and YAKE to process and analyze the input text.

**`Features`**
`Named Entity Recognition (NER)`: Extracts entities like persons, organizations, locations, etc., from the input content using SpaCy.
`Keyword Extraction`: Identifies significant keywords from the content using YAKE and TextBlob.
`Comparison of Noun Phrases`: Compares noun phrases extracted using TextBlob and SpaCy.
`Existing Tags Analysis`: Compares input tags with extracted entities and keywords, highlighting matches and suggesting new tags.
`Dynamic HTML Output`: Presents the analysis results in a user-friendly HTML format.

**`How to Use`**
- Inputs: Fill in the title, summary, content, and existing tags (comma-separated) in the provided fields.
- Analysis: Click the "Analyze" button to process the input.
- Results: View the results displayed in HTML format, including matched and unmatched tags, extracted keywords, and a comparison of noun phrases.

**`Requirements`**
- Python 3.7+
- Gradio
- SpaCy
- TextBlob
- YAKE
- Pandas
