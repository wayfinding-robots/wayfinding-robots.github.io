import bibtexparser
import re
import argparse
import os

def remove_ordinals(text):
    """remove english ordinal words from venue names"""
    ordinals = [
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
        "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth", 
        "eighteenth", "nineteenth", "twentieth", "thirtieth", "fortieth", "fiftieth"
    ]
    
    # compound patterns (e.g., "twenty-first", "eighty-eighth")
    compound_pattern = r'\b(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[-](?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b'
    
    # numeric pattern (e.g., "1st", "2nd", "3rd", "4th", "7th")
    numeric_ordinal_pattern = r'\b\d+(?:st|nd|rd|th)\b'
    
    # remove standalone ordinals with word boundaries
    for ordinal in ordinals:
        text = re.sub(r'\b' + ordinal + r'\b', '', text, flags=re.IGNORECASE)
    
    # remove compound, numeric
    text = re.sub(compound_pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(numeric_ordinal_pattern, '', text, flags=re.IGNORECASE)
    
    # fix white space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def bib_to_markdown(bib_file, citation_keys_string):
    # citation keys is some comma-seperated string of keys in your bibtex to extract from
    # e.g., "smith2025robotmodel, robters1996psychological"
    citation_keys = [k.strip() for k in citation_keys_string.split(", ")]
    
    # nice parsing library https://bibtexparser.readthedocs.io/en/main/
    library = bibtexparser.parse_file(bib_file) 

    # substitute some words for mainstream publisher names / acronyms
    pubs = {
        'IEEE': 'IEEE', 
        'Institute of Electrical and Electronics Engineers': 'IEEE',
        'Association for Computing Machinery': 'ACM',
        'Springer': 'Springer',
        'Springer Nature': 'Springer', 
        'Springer-Verlag': 'Springer', 
        'Springer US': 'Springer', 
        'Springer International Publishing': 'Springer', 
        'Springer Berlin Heidelberg': 'Springer',
        'Springer Netherlands': 'Springer',
        'Springer Nature Switzerland AG': 'Springer',
        'Springer Singapore': 'Springer',
        'Springer Verlag': 'Springer',
        'Springer Verlag Berlin Heidelberg': 'Springer',
        'Springer Verlag London Limited': 'Springer',
        'Elsevier': 'Elsevier', 
        'Elsevier B.V.': 'Elsevier',
        'Elsevier Inc.': 'Elsevier',
        'Elsevier Ltd.': 'Elsevier',
        'Elsevier Science': 'Elsevier',
        'Taylor and Francis': 'Taylor & Francis',
        'Taylor & Francis': 'Taylor & Francis',
        'Wiley': 'Wiley', 
        'Wiley Periodicals LLC': 'Wiley',
        'Wiley Interscience': 'Wiley',
        'Wiley Online Library': 'Wiley',
        'Wiley-Blackwell Publishing, Inc.': 'Wiley',
        'Wiley-Blackwell Publishing Ltd.': 'Wiley',
        'Wiley-Blackwell Publishing': 'Wiley',
        'Wiley-Blackwell': 'Wiley',
        'Wiley-VCH Verlag GmbH & Co. KGaA, Weinheim': 'Wiley',
        'Wiley-VCH Verlag GmbH & Co. KGaA': 'Wiley',
        'Wiley-VCH Verlag GmbH': 'Wiley',
        'Wiley-VCH Verlag': 'Wiley',
        'Wiley-VCH': 'Wiley',
        'MDPI': 'MDPI',
    }

    # add acronyms to well-known venues for easier identification
    venue_abbreviations = {
        "Robotics and Automation Letters": "RA-L",
        "Transactions on Biomedical Engineering": "TBME",
        "International Conference on Intelligent Robots and Systems": "IROS",
        "International Conference on Robotics and Automation": "ICRA",
        "Systems, Man, and Cybernetics": "SMC",
        "Human-Robot Interaction": "HRI",
        "Robotics and Biomimetics": "ROBIO",
        "Robot and Human Interactive Communication": "RO-MAN",
        "Robotics and Automation Magazine": "RAM",
        "Transactions on Neural Systems and Rehabilitation Engineering": "TNSRE",
        "Transactions on Automation Science and Engineering": "TASE",
        "Transactions on Robotics and Automation": "T-RO",
        "International Journal of Robotics Research": "IJRR",
        "Journal of Field Robotics": "JFR",
        "Journal of Robotics and Autonomous Systems": "JRAS",
        "Journal of Autonomous Robots": "JAR",
        "Journal of Machine Learning Research": "JMLR",
        "Journal of Computer Vision": "IJCV",
        "Journal of Artificial Intelligence Research": "JAIR",
        "Artificial Intelligence Review": "AIR",
        "Artificial Intelligence Journal": "AIJ",
        "International Journal of Computer Vision": "IJCV",
        "Transactions on Pattern Analysis and Machine Intelligence": "TPAMI",
        "European Conference on Computer Vision": "ECCV",
        "International Conference on Computer Vision": "ICCV",
        "Computer Vision and Pattern Recognition": "CVPR",
        "Neural Information Processing Systems": "NeurIPS",
        "International Conference on Learning Representations": "ICLR",
        "International Conference on Machine Learning": "ICML",
        "International Conference on Artificial Intelligence and Statistics": "AISTATS",
        "International Joint Conference on Artificial Intelligence": "IJCAI",
    }
    
    entries_with_years = []
    problematic_keys = []
    found_keys = set()
    
    for entry in library.entries:
        if entry.key in citation_keys:
            found_keys.add(entry.key)

            # fields list into dictionary keys; all case insensitive
            fields = {f.key.lower(): f.value.strip('"{}') for f in entry.fields}
            
            # extract with defaults if err, not found (used later below)
            title = fields.get("title", "Untitled")
            year = fields.get("year", "n.d.")
            doi = fields.get("doi", "")
            publisher = fields.get("publisher", "Unknown Publisher")
            venue = fields.get("journal") or fields.get("booktitle", "Unknown Venue")
            
            # arXiv papers have eprint and prefix fields, instead of booktitle or journal
            eprint = fields.get("eprint", "")
            archive_prefix = fields.get("archiveprefix", "").lower()
            
            # figure out URL with preference order: 
            # 1. regular URL if available (url tag)
            # 2. DOI link if available (doi tag)
            # 3. arXiv link if it's an arXiv paper (eprint tag)
            # 4. Empty string if none available (a lot of springer bibtexs hit here)
            if "url" in fields:
                url = fields["url"]
            elif doi:
                url = f"https://doi.org/{doi}"
            elif archive_prefix == "arxiv" and eprint:
                url = f"https://arxiv.org/abs/{eprint}"
            else:
                url = ""
            
            # arxiv can be a venue, its just not directly explicit
            if venue == "Unknown Venue" and archive_prefix == "arxiv":
                venue = "arXiv"
            
            # chop ordinals from full venue name, as well as other terms, or add publisher to venue
            venue = remove_ordinals(venue)
            if str(year) in venue:
                venue = venue.replace(str(year)+" ", "")
            if re.search(r'proceedings of the', venue, re.IGNORECASE):
                venue = re.sub(r'proceedings of the ', '', venue, flags=re.IGNORECASE)
            if re.search(r'annual', venue, re.IGNORECASE):
                venue = re.sub(r'annual ', '', venue, flags=re.IGNORECASE)
            if publisher != "" and publisher in pubs.keys() and (publisher not in venue and pubs[publisher] not in venue):
                venue = pubs[publisher] + " " + venue
            if ("mdpi" in url.lower() or "mdpi" in doi.lower()) and publisher == "Unknown Publisher":
                venue = "MDPI " + venue
            
            for full_name, abbreviation in venue_abbreviations.items():
                if full_name in venue and abbreviation not in venue:
                    venue += f" ({abbreviation})"

            # Check if entry has missing essential information
            # sanity check; e.g., theses usually are marked as such
            is_problematic = (title == "Untitled" or venue == "Unknown Venue" or year == "n.d.")
            
            # note which citation key part of problematic entries
            citation_info = f" [Key: {entry.key}]" if is_problematic else ""
            if is_problematic:
                problematic_keys.append(entry.key)
            
            # markdown formatting for ez insert to readme
            md_entry = f"- [{title}]({url}), *{venue}*, {year}{citation_info}"
            
            # cast to year to help sort easier below
            try:
                year_int = int(year)
            except ValueError:
                year_int = float('inf')  # Non-numeric years go at the end
                
            entries_with_years.append((year_int, md_entry))
    
    # if keys aren't in .bib file; probably there is input typo
    missing_keys = set(citation_keys) - found_keys
    for key in missing_keys:
        md_entry = f"- [Untitled](), *Unknown Venue*, n.d. [Missing Key: {key}]"
        problematic_keys.append(key)
        entries_with_years.append((float('inf'), md_entry))
    
    # sort output (ascending order, newest first)
    entries_with_years.sort(key=lambda x: x[0])
    entries_with_years.reverse()  # Newest first
    
    # get markdown entries for printing
    md_entries = [entry for _, entry in entries_with_years]
    
    # show problem keys
    if problematic_keys:
        print(f"Warning: The following citation keys have incomplete information: {', '.join(problematic_keys)}")
    
    return md_entries


if __name__ == "__main__":
    # Argument parser setup
    parser = argparse.ArgumentParser(description="Convert BibTeX entries to Markdown format.")
    parser.add_argument("--bib_path", "-b", type=str, default="references.bib", help="Path to the BibTeX file.")
    parser.add_argument("--citation_keys", "-c", type=str, help="Comma-separated list of citation keys.")
    args = parser.parse_args()

    bib_file = args.bib_path
    citation_keys_string = args.citation_keys

    markdown_refs = bib_to_markdown(bib_file, citation_keys_string)
    print("\n".join(markdown_refs))

