import os
import re
import html
from bs4 import BeautifulSoup as bs
import requests
import spacy
import yake
from textblob import TextBlob
from rich.console import Console
from rich.table import Table
from rich import box
from fuzzywuzzy import process, fuzz
from urllib.parse import urlparse
import nltk
from nltk.corpus import stopwords

stop_words = set(stopwords.words('english'))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
nlp = spacy.load('en_core_web_sm')
console = Console()

HARD_CODED_KEYWORDS = {
    "bollywood": ["bollywood", "movie industry","shahid kapoor","urvashi rautela"],
    "tollywood": ["tollywood", "telugu cinema", "allu arjun", "movie review", "mahesh babu"],
    "kollywood": ["kollywood", "tamil cinema", "thalapathy vijay"],
    "sandalwood": ["sandalwood", "kannada cinema", "actor darshan", "kicha suddep"],
    "hollywood": ["hollywood", "film industry", "tom cruise"],
    "lifestyle": ["yoga", "horoscope", "beauty"],
    "cookery": ["recipe", "cook"],
    "electricity": ["power outage"]
}

def clean_text(content):
    content = html.unescape(content).strip()
    content = re.sub(r"https?://\S+|pic\.twitter\.com/\S+|<.*?>|(&[^;]+;)", " ", content).replace("\\", "")
    content = re.sub(r'[.,:\'"-]', '', content)  
    content = re.sub(r"\s+", " ", content)  
    return content

def fetch_xml_content(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  
        return response.content
    except requests.RequestException as e:
        print(f"Error fetching content from {url}: {e}")
        return None

def remove_articles(text):
    text = re.sub(r'[.,:\'"-]', '', text) 
    return re.sub(r'\b(a|an|the)\b', '', text).strip()

def clean_and_filter_phrases(phrases):
    filtered_phrases = set()
    for phrase in phrases:
        phrase = re.sub(r'\b(a|an|the)\b', '', phrase).strip()
        words = [word for word in phrase.split() if word.lower() not in stop_words]
        cleaned_phrase = ' '.join(words)
        if cleaned_phrase:
            filtered_phrases.add(cleaned_phrase.lower())
    return filtered_phrases

def extract_ner_tags(text):
    doc = nlp(text)
    persons = [remove_articles(ent.lemma_.lower()) for ent in doc.ents if ent.label_ == 'PERSON']
    orgs = [remove_articles(ent.lemma_.lower()) for ent in doc.ents if ent.label_ == 'ORG']
    gpes = [remove_articles(ent.lemma_.lower()) for ent in doc.ents if ent.label_ == 'GPE']
    norps = [remove_articles(ent.lemma_.lower()) for ent in doc.ents if ent.label_ == 'NORP']
    events = [remove_articles(ent.lemma_.lower()) for ent in doc.ents if ent.label_ == 'EVENT']
    return list(set(persons)), list(set(orgs)), list(set(gpes)), list(set(norps)), list(set(events))

def extract_textblob_noun_phrases(text):
    blob = TextBlob(text)
    return clean_and_filter_phrases(blob.noun_phrases)

def extract_yake_keywords(text, max_keywords=10):
    kw_extractor = yake.KeywordExtractor()
    keywords = kw_extractor.extract_keywords(text)
    return clean_and_filter_phrases(kw[0] for kw in keywords[:max_keywords])

def read_existing_tags(filepath='updated_tags.txt'):    # Attach your .txt file here
    try:
        with open(filepath, 'r') as file:
            return {line.strip().lower() for line in file.readlines()}
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return set()

def highlight_text(text, tags):
    highlighted_text = text
    tags = {remove_articles(tag) for tag in tags}
    for tag in tags:
        highlighted_text = re.sub(r'\b{}\b'.format(re.escape(tag)), lambda match: f"[spring_green1]{match.group(0)}[/spring_green1]", highlighted_text, flags=re.IGNORECASE)
    return highlighted_text

def print_ner_table(title, content, existing_tags):
    title_persons, title_orgs, title_gpes, title_norps, title_events = extract_ner_tags(title)
    content_persons, content_orgs, content_gpes, content_norps, content_events = extract_ner_tags(content)

    combined_persons = list(set(title_persons + content_persons))
    combined_orgs = list(set(title_orgs + content_orgs))
    combined_gpes = list(set(title_gpes + content_gpes))
    combined_norps = list(set(title_norps + content_norps))
    combined_events = list(set(title_events + content_events))

    combined_tags = set(combined_persons + combined_orgs + combined_gpes + combined_norps + combined_events)

    highlighted_title = highlight_text(title, combined_tags)
    highlighted_content = highlight_text(content, combined_tags)

    print_matched_unmatched_table(combined_persons, existing_tags, "Persons")
    print_matched_unmatched_table(combined_orgs, existing_tags, "Organizations")
    print_matched_unmatched_table(combined_gpes, existing_tags, "GPEs")
    print_matched_unmatched_table(combined_norps, existing_tags, "NORPs")
    print_matched_unmatched_table(combined_events, existing_tags, "Events")

    return combined_persons, combined_orgs, combined_gpes, combined_norps, combined_events, highlighted_title, highlighted_content

def print_matched_unmatched_table(ner_tags, existing_tags, category):
    table = Table(box=box.SQUARE)
    table.add_column("NER Tags")
    table.add_column("Matched Tags")
    table.add_column("Unmatched Tags - Suggestable Tags")

    existing_tags_preprocessed = {tag.lower().strip() for tag in existing_tags}

    for tag in ner_tags:
        tag_cleaned = remove_articles(tag.lower().strip())
        matched = tag if tag_cleaned in existing_tags_preprocessed else ''
        unmatched = '' if tag_cleaned in existing_tags_preprocessed else tag
        table.add_row(tag, matched, unmatched)

    console.print(f"\n NER Matched and Unmatched Tags:")
    console.print(f"\n Unmatched Tags can be used as suggestable tags.")
    console.print(table)

def extract_tags(item):
    tags_text = item.find('Tags').text.strip()
    return [tag.strip().lower() for tag in tags_text.split(',') if tag.strip()]

def extract_category(url, base_url):
    parsed_url = urlparse(url)    
    path = parsed_url.path.replace(base_url, '', 1)   
    category = re.sub(r'/\d+\.xml$', '', path)   
    category = category.split('/')[-1]   
    return category
    
def print_tags_check(tags, title, content, ner_tags):
    combined_persons, combined_orgs, combined_gpes, combined_norps, combined_events = ner_tags
    all_combined_tags = set(combined_persons + combined_orgs + combined_gpes + combined_norps + combined_events)

    title = clean_text(title).lower()
    content = clean_text(content).lower()

    tags_table = Table(box=box.SQUARE)
    tags_table.add_column("Existing Tags")
    tags_table.add_column("Found in NER Tags Table")
    tags_table.add_column("Found in Title/Content")
    
    extracted_tags_table = Table(box=box.SQUARE)
    extracted_tags_table.add_column("Extracted Tags")
    extracted_tags_table.add_column("Matched Text Tags")

    def check_partial_phrase(tag, combined_tags, text):
        words = re.sub(r'[.,:\'"-]', '', tag).split()
        text = re.sub(r'[.,:\'"-]', '', text)  
        tag_phrases = [tag]
        
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                tag_phrases.append(' '.join(words[i:j]))
        
        return [phrase for phrase in tag_phrases if phrase in combined_tags or phrase in text]

    for tag in tags:
        tag_cleaned = tag.lower().strip()
        
        found_in_ner = tag_cleaned in all_combined_tags
        found_in_text = tag_cleaned in (title + ' ' + content)
        
        if not found_in_ner:
            found_in_ner = any(tag_cleaned == t.lower() for t in all_combined_tags)
        if not found_in_text:
            found_in_text = any(tag_cleaned == t.lower() for t in (title + ' ' + content).split())
       
        partial_matches = check_partial_phrase(tag_cleaned, all_combined_tags, title + ' ' + content)
        found_in_text_str = ", ".join(partial_matches) if partial_matches else "Not Found"
        
        tags_table.add_row(tag, "Yes" if found_in_ner else "No", "Yes" if found_in_text else "No")
        
        extracted_tags_table.add_row(tag, found_in_text_str)
    
    console.print("\nExisting Tags from XML Page and Their Presence:")
    console.print(tags_table)
    
    console.print("\nExtracted Tags and Their Matched Text Tags:")
    console.print(extracted_tags_table)

    existing_tags = read_existing_tags()
    all_combined_tags = set(combined_persons + combined_orgs + combined_gpes + combined_norps + combined_events)

    def find_fuzzy_matches(tags, existing_tags):
        matches = []
        for tag in tags:
            tag_cleaned = tag.lower().strip()
            best_match, best_score = process.extractOne(
                tag_cleaned,
                existing_tags,
                scorer=fuzz.token_sort_ratio 
            )
            if best_score >= 80: 
                matches.append((tag, best_match))
        return matches

    fuzzy_matches = find_fuzzy_matches(tags, existing_tags)
    if fuzzy_matches:
        console.print("\nThis fuzzy_matches checks whether Existing Tags(from XML Page) is present in Tags file.")
        console.print("\nFuzzy Matched Tags(With Tags File):")
        for tag, match in fuzzy_matches:
            console.print(f"{tag} -> {match}")
    else:
        console.print("\nNo fuzzy matches found(With Tags File).")

def find_similar_tags(xml_tags, title, content):
    combined_text = ' '.join([title, content]).lower()
    similar_tags = []

    for tag in xml_tags:
        tag_cleaned = remove_articles(tag.lower().strip())
        
        words = tag_cleaned.split()
        for i in range(len(words)):
            for j in range(i + 1, len(words) + 1):
                phrase = ' '.join(words[i:j])
                if phrase in combined_text:
                    similar_tags.append((tag, phrase))
                    break
    
        best_match, best_score = process.extractOne(tag_cleaned, combined_text.split(), scorer=fuzz.token_sort_ratio)
        if best_score >= 80:  
            similar_tags.append((tag, best_match))

    similar_tags = list(set(similar_tags))    
    return similar_tags

def print_comparison_table(text):
    textblob_noun_phrases = list(extract_textblob_noun_phrases(text))

    doc = nlp(text)
    spacy_noun_phrases = list(clean_and_filter_phrases(chunk.text for chunk in doc.noun_chunks))

    yake_keywords = list(extract_yake_keywords(text))

    table = Table(box=box.SQUARE)
    table.add_column("TextBlob Noun Phrases", style="bold color(208)")
    table.add_column("Spacy Noun Phrases", style="grey93")
    table.add_column("YAKE Keywords", style="green1")

    max_length = max(len(textblob_noun_phrases), len(spacy_noun_phrases), len(yake_keywords))

    for i in range(max_length):
        textblob_phrase = textblob_noun_phrases[i] if i < len(textblob_noun_phrases) else ""
        spacy_phrase = spacy_noun_phrases[i] if i < len(spacy_noun_phrases) else ""
        yake_keyword = yake_keywords[i] if i < len(yake_keywords) else ""
        table.add_row(textblob_phrase, spacy_phrase, yake_keyword)

    console.print("\nComparison of TextBlob Noun Phrases, Spacy Noun Phrases, and YAKE Keywords:")
    console.print(table)
    
def find_hardcoded_keywords(text):
    found_keywords = {}
    for keyword, phrases in HARD_CODED_KEYWORDS.items():
        for phrase in phrases:
            if phrase in text.lower():
                if keyword not in found_keywords:
                    found_keywords[keyword] = []
                found_keywords[keyword].append(phrase)
    return found_keywords

def main(url):
    xml_content = fetch_xml_content(url)
    if xml_content is None:
        return

    root = bs(xml_content, 'xml')
    items = root.find_all('Item')

    existing_tags = read_existing_tags()

    for item in items:
        inner_link = item.find('Link').text.strip().replace('https://rss.', 'https://rss1.')
        title = item.find('Title').text.strip()
        tags = extract_tags(item)

        cleaned_title = clean_text(title)

        inner_content = fetch_xml_content(inner_link)
        if inner_content:
            inner_soup = bs(inner_content, 'html.parser')
            inner_text = clean_text(inner_soup.find('content').text if inner_soup.find('content') else inner_soup.get_text())
        else:
            inner_text = "Content not available"
        
        category = extract_category(inner_link, "https://rss1.oneindia.com/xml4apps/www.oneindia.com/")  

        print(f"URL: {inner_link}")
        print(f"Category: {category}")
        print("----------------------------------------------------------------------------------------------------------------------------------------------------")
   
        combined_persons, combined_orgs, combined_gpes, combined_norps, combined_events, highlighted_title, highlighted_content = print_ner_table(cleaned_title, inner_text, existing_tags)
   
        console.print(f"\nHighlighted Title:\n{highlighted_title}")
        console.print(f"\nHighlighted Content:\n{highlighted_content}")
   
        print_tags_check(tags, cleaned_title, inner_text, (combined_persons, combined_orgs, combined_gpes, combined_norps, combined_events))
        
        print_comparison_table(inner_text)
        
        similar_tags = find_similar_tags(tags, cleaned_title, inner_text)
        if similar_tags:
            console.print("\nSimilar Phrases that are found in Title & Content:")
            for tag, match in similar_tags:
                console.print(f"Tag: {tag} -> Similar Phrases found: {match}")
        else:
            console.print("\nNo similar tags found.")

        hardcoded_keywords = find_hardcoded_keywords(inner_text)
        if hardcoded_keywords:
            console.print("\nHardcoded Keywords Found:")
            for category, phrases in hardcoded_keywords.items():
                console.print(f"{category.capitalize()}: {', '.join(phrases)}")
        else:
            console.print("\nNo hardcoded keywords found.")
        
        console.print("----------------------------------------------------------------------------------------------------------------------------------------------------")

url = "https://rss1.oneindia.com/xml4apps/www.oneindia.com/latest.xml"  # Replace this with XML source link.
main(url)
