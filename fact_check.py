import os
import sys
import requests
from github import Github, GithubException
import subprocess
import json
from duckduckgo_search import ddg
import openai
import tiktoken

openai.api_key = sys.argv[6]

token_usage = {'prompt': 0, 'completion': 0}

def count_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0301")
    return len(encoding.encode(text))


def openai_call(
        prompt: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.5,
        max_tokens: int = 500,
):
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=1,
        stop=None,
    )
    ret = response.choices[0].message.content.strip()
    token_usage['prompt'] += count_tokens(prompt)
    token_usage['completion'] += count_tokens(ret)
    return ret

def google_search(query):
    return '\n\n----'.join([x['title']+'\n'+x['body'] for x in ddg(query)[:4]])



EXTRACT_STATEMENTS = '''```%s```

Extract all the claims that can be fact-checked from the text section. For each claim, generate a search query that includes the claim and at least one relevant keyword. Critical: the output must be machine-readable, and formatted as json:
```[{"claim": "", "query": ""}, {"claim": "", "query": ""}]```
'''


VERIFY_STATEMENT = '''
Given a claim and a set of search results from a search engine API, determine whether the claim is true or false, or if there is not enough evidence to verify it. Use the search results to provide evidence for your determination.

The claim to be verified is: ```%s```

The search results are as follows: ```%s```

Based on the search results, is the claim true, false, or not able to be verified? If the claim is false, provide a brief explanation and reference your sources. If the claim is true or not able to be verified, provide a brief explanation and reference your sources as necessary.

Output should be machine-readable, for example:
```{
    "claim": "",
    "verdict": true|false|can't verify,
    "explanation": ""
}```'''

def get_pull_request():
    # Get the arguments passed to the script
    repo_url = sys.argv[1]
    head_branch = sys.argv[2]
    base_branch = sys.argv[3]
    pull_request_number = int(sys.argv[4])
    token = sys.argv[5]

    # Get the authentication token from the environment variable
    #token = os.environ.get("GITHUB_TOKEN")

    # Initialize the Github object
    g = Github(token)

    repo_name = "/".join(repo_url.split("/")[-2:]).replace(".git", "")

    # Get the repository object for the pull request
    repo = g.get_repo(repo_name)

    # Get the pull request object
    pull_request = repo.get_pull(pull_request_number)
    return pull_request
    
def get_diff(pull_request):
    repo_url = sys.argv[1]
    head_branch = sys.argv[2]
    base_branch = sys.argv[3]
    pull_request_number = int(sys.argv[4])
    token = sys.argv[5]
    # Get the diff for the pull request
    #diff_url = f"{repo_url}/compare/{base_branch}...{head_branch}.diff"
    #diff_response = requests.get(diff_url)

    # Get the repository path on the runner
    repo_path = os.environ['GITHUB_WORKSPACE']
    print('repo_path', repo_path)

    # Check out the base branch and head branch
    print('git0', subprocess.run(['git', 'fetch', '--prune', '--unshallow'], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False))
    print('git1', subprocess.run(['git', 'checkout', base_branch], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False))
    print('git2', subprocess.run(['git', 'checkout', head_branch], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False))

    # Get the diff for the pull request
    diff_output = subprocess.check_output(['git', 'diff', '--no-prefix', '--unified=0', base_branch, head_branch], cwd=repo_path)

    # Convert the bytes to a string
    diff_str = diff_output.decode('utf-8')

    # Print the diff
    return diff_str
    
pull_request = get_pull_request()
diff_str = get_diff(pull_request)
# Print the diff
print(diff_str)

# Break into segments

parts = diff_str.split('\n##')
# to do: split long parts

# Get statements from each segment

wrong = []
claims = []
had_error = False
for p in parts:
    if len(p.strip()) <= 1:
        continue
    ans = openai_call(EXTRACT_STATEMENTS % p)
    print("Prompt: " + EXTRACT_STATEMENTS % p)
    ans = ans.strip().strip('`').strip()
    ans = ans[ans.find('['):]
    print("Answer: " + ans)
    try:
        obj = json.loads(ans)
    except Exception as ex:
        print(ex)
        had_error = True
        pass
    
    for s in obj:
        claims.append(s)
        try:
            summary = google_search(s['query'])
        except Exception as ex:
            print(ex)
            had_error = True
            continue
        print("Query: " + s['query'])
        print("Summary: " + summary) 
        try:
            ans = openai_call(VERIFY_STATEMENT % (s['claim'], summary))
        except Exception as ex:
            print(ex)
            had_error = True
            continue
        print("Prompt: "+ VERIFY_STATEMENT % (s['claim'], summary))
        ans = ans.strip().strip('`').strip()
        ans = ans[ans.find('{'):]
        print("Answer: " + ans)
        try:
            obj = json.loads(ans)
            if obj['verdict'] != 'true' && obj['verdict'] != True:
                wrong.append(obj)
        except Exception as ex:
            print(ex)
            had_error = True
        
print("False claims: ")
comment = ''


for obj in wrong:    
        comment += f"Found false claim " + obj['claim'] + ". " + obj['explanation']
        
if had_error:
    comment +=  f"Fact-check failed due to errors"
     
if comment != '':
    pull_request.create_issue_comment(comment)
            
print('token_usage', token_usage)