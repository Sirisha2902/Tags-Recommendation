import gradio as gr
import spacy
import pandas as pd
from textblob import TextBlob
from yake import KeywordExtractor
from spacy.lang.en.stop_words import STOP_WORDS

nlp = spacy.load("en_core_web_sm")

def read_updated_tags(file_path):
    try:
        with open(file_path, 'r') as file:
            tags = [line.strip().lower() for line in file.readlines()]
        return set(tags)  
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return set()

def analyze_text(title, summary, content, existing_tags, updated_tags_file):
    updated_tags = read_updated_tags(updated_tags_file)
    doc_content = nlp(content)
    
    entity_types = ['PERSON', 'ORG', 'GPE', 'NORP', 'EVENT']
    ner_tags = list(set(ent.text.lower() for ent in doc_content.ents if ent.label_ in entity_types))

    matched_tags = set()
    unmatched_tags = set()
    for tag in ner_tags:
        if tag in updated_tags:
            matched_tags.add(tag)
        else:
            unmatched_tags.add(tag)
    
    ner_tags_df = pd.DataFrame({
        'NER Tags': list(ner_tags),
        'Matched Tags': [tag if tag in updated_tags else '' for tag in ner_tags],
        'Unmatched Tags - Suggestable Tags': [tag if tag not in updated_tags else '' for tag in ner_tags]
    }).drop_duplicates().reset_index(drop=True)

    existing_tags = list(set(tag.strip().lower() for tag in existing_tags))
    existing_tags_df = pd.DataFrame({
        'Existing Tags': existing_tags,
        'Found in NER Tags Table': [tag if tag in ner_tags else 'No' for tag in existing_tags],
        'Found in Title/Content': [tag if tag in title.lower() or tag in summary.lower() or tag in content.lower() else 'No' for tag in existing_tags]
    }).drop_duplicates().reset_index(drop=True)
    
    textblob_phrases = list(set(TextBlob(content).noun_phrases))
    spacy_noun_chunks = list(set(chunk.text for chunk in nlp(content).noun_chunks))
    yake_keywords = list(set(keyword for keyword, _ in KeywordExtractor().extract_keywords(content)))
    
    textblob_phrases = [phrase for phrase in textblob_phrases if phrase.lower() not in STOP_WORDS]
    spacy_noun_chunks = [chunk for chunk in spacy_noun_chunks if chunk.lower() not in STOP_WORDS]
    yake_keywords = [keyword for keyword in yake_keywords if keyword.lower() not in STOP_WORDS]
    
    max_length = max(len(textblob_phrases), len(spacy_noun_chunks), len(yake_keywords))
    textblob_phrases += [''] * (max_length - len(textblob_phrases))
    spacy_noun_chunks += [''] * (max_length - len(spacy_noun_chunks))
    yake_keywords += [''] * (max_length - len(yake_keywords))
    
    extracted_tags = {}
    for tag in existing_tags:
        matches = []
        if tag in title.lower():
            matches.append(f"Title: {tag}")
        if tag in summary.lower():
            matches.append(f"Summary: {tag}")
        if tag in content.lower():
            matches.append(f"Content: {tag}")
        if matches:
            extracted_tags[tag] = matches

    extracted_tags_df = pd.DataFrame({
        'Extracted Tags': list(extracted_tags.keys()),
        'Matched Text Tags': [', '.join(set(tags)) for tags in extracted_tags.values()] 
    }).drop_duplicates().reset_index(drop=True)

    comparison_df = pd.DataFrame({
        'TextBlob Noun Phrases': textblob_phrases,
        'Spacy Noun Phrases': spacy_noun_chunks,
        'YAKE Keywords': yake_keywords
    }).drop_duplicates().reset_index(drop=True)

    comparison_df = comparison_df.head(20)
    
    ner_tags_html = ner_tags_df.to_html(index=False)
    existing_tags_html = existing_tags_df.to_html(index=False)
    extracted_tags_html = extracted_tags_df.to_html(index=False)
    comparison_html = comparison_df.to_html(index=False)
    
    return (ner_tags_html, existing_tags_html, extracted_tags_html, comparison_html)

def gradio_interface(title, summary, content, existing_tags):
    updated_tags_file = 'updated_tags.txt'
    return analyze_text(title, summary, content, existing_tags, updated_tags_file)

with gr.Blocks() as demo:
    gr.Markdown("# Text Analysis Interface")
    with gr.Row():
        title_input = gr.Textbox(label="Title")
        summary_input = gr.Textbox(label="Summary")
        content_input = gr.Textbox(label="Content", lines=10)
        existing_tags_input = gr.Textbox(label="Existing Tags (comma-separated)")
    
    output_html = gr.HTML()
    
    def process_inputs(title, summary, content, existing_tags):
        if not title.strip():
            return "Please fill in the Title input."
        if not summary.strip():
            return "Please fill in the Summary input."
        if not content.strip():
            return "Please fill in the Content input."
        
        existing_tags_list = [tag.strip().lower() for tag in existing_tags.split(',')]
        ner_tags_html, existing_tags_html, extracted_tags_html, comparison_html = gradio_interface(title, summary, content, existing_tags_list)
        
        return ner_tags_html + "<br>" + existing_tags_html + "<br>" + extracted_tags_html + "<br>" + comparison_html

    submit_btn = gr.Button("Analyze")
    submit_btn.click(process_inputs, inputs=[title_input, summary_input, content_input, existing_tags_input], outputs=output_html)

demo.launch()
