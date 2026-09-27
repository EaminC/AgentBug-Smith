import json
import re
import sys
import os
import shutil
from datetime import datetime

def calculate_text_similarity(text1, text2):
    """Calculates keyword intersection between two texts."""
    if not text1 or not text2:
        return 0.0
    
    # Simple stopword list
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'to', 'in', 'on', 'for', 'with', 'by', 'at', 'of'}
    
    def get_keywords(text):
        words = re.findall(r'\w+', text.lower())
        return set(w for w in words if w not in stopwords and len(w) > 2)

    set1 = get_keywords(text1)
    set2 = get_keywords(text2)
    
    if not set1 or not set2:
        return 0.0
        
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    return len(intersection) / len(union)

def verify_issue_pr_link(data):
    """
    Verifies the link between an issue and its PRs.
    Returns the highest confidence score found among linked PRs.
    """
    issue_number = data.get('number')
    issue_title = data.get('title', '')
    issue_body = data.get('body', '')
    
    print(f"\n🔍 Verifying links for Issue #{issue_number}: \"{issue_title}\"")
    
    linked_prs = data.get('linked_prs', [])
    if not linked_prs:
        print("❌ No linked PRs found in the data.")
        return -100 # Return a low score if no PRs exist

    max_score = -100

    for pr in linked_prs:
        pr_number = pr.get('number')
        pr_title = pr.get('title', '')
        pr_body = pr.get('body', '')
        
        # print(f"👉 Analyzing PR #{pr_number}: \"{pr_title}\"")
        
        reasons = []
        score = 0
        
        # 1. Check for Magic Closing Keywords
        closing_pattern = r'(?i)(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+.*#{}'.format(issue_number)
        
        if re.search(closing_pattern, pr_body):
            score += 50
            reasons.append("✅ PR body contains explicit closing keyword")
        else:
            reasons.append("❌ PR body DOES NOT contain explicit closing keywords")

        # 2. ID Distance Heuristic
        # If Issue is #3 and PR is #9000+, they are likely years apart.
        id_diff = abs(pr_number - issue_number)
        if id_diff > 1000:
            score -= 20
            reasons.append(f"⚠️ Massive ID gap ({id_diff}).")
        
        # 3. Text Similarity
        similarity = calculate_text_similarity(issue_title + " " + issue_body, pr_title + " " + pr_body)
        similarity_percentage = round(similarity * 100, 2)
        
        if similarity > 0.1:
            score += 10
            reasons.append(f"✅ Content seems relevant (Sim: {similarity_percentage}%)")
        else:
            score -= 10
            reasons.append(f"❌ Content seems unrelated (Sim: {similarity_percentage}%)")

        # 4. Keyword Check from Issue Title
        issue_keywords = set(re.findall(r'\w+', issue_title.lower())) - {'the', 'to', 'a', 'in'}
        pr_keywords = set(re.findall(r'\w+', pr_title.lower()))
        common_keywords = issue_keywords.intersection(pr_keywords)
        
        if common_keywords:
             reasons.append(f"✅ Shared keywords: {common_keywords}")
        else:
             reasons.append("❌ No shared keywords in title")

        # Track the best score among all linked PRs
        if score > max_score:
            max_score = score
        
        # Optional: Print details if needed (commented out for cleaner bulk output)
        # for reason in reasons:
        #     print(f"   - {reason}")

    print(f"   Best Confidence Score: {max_score}")
    if max_score > 30:
            print(f"   🟢 VERDICT: Likely the correct PR.")
    elif max_score >= 0:
            print(f"   🟡 VERDICT: Possible, but manual review needed.")
    else:
            print(f"   🔴 VERDICT: Highly unlikely to be the correct PR.")
            
    return max_score

if __name__ == "__main__":
    # Configuration
    SOURCE_DIR = "data/issue-filtered"
    CHECK_DIR = "data/issue-filtered-check"
    FAIL_DIR = "data/issue-filtered-fail"

    # Ensure source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' does not exist.")
        sys.exit(1)

    # Create destination directories if they don't exist
    os.makedirs(CHECK_DIR, exist_ok=True)
    os.makedirs(FAIL_DIR, exist_ok=True)

    # List all JSON files
    files = [f for f in os.listdir(SOURCE_DIR) if f.startswith("issue_") and f.endswith(".json")]
    
    print(f"Found {len(files)} files to process in {SOURCE_DIR}...")

    for filename in files:
        filepath = os.path.join(SOURCE_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            score = verify_issue_pr_link(data)
            
            # Move files based on score criteria
            if score > 30:
                # Keep in same folder
                pass
            elif 0 <= score <= 30:
                # Move to check folder
                dest_path = os.path.join(CHECK_DIR, filename)
                shutil.move(filepath, dest_path)
                print(f"   -> Moved to {CHECK_DIR}")
            else:
                # Move to fail folder (score < 0)
                dest_path = os.path.join(FAIL_DIR, filename)
                shutil.move(filepath, dest_path)
                print(f"   -> Moved to {FAIL_DIR}")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON in {filename}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred processing {filename}: {e}")

    print("\nProcessing complete.")