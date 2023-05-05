import os
import sys
import requests
from github import Github, GithubException

# Get the arguments passed to the script
repo_url = sys.argv[1]
head_branch = sys.argv[2]
base_branch = sys.argv[3]
pull_request_number = int(sys.argv[4])

# Get the authentication token from the environment variable
token = os.environ.get("GITHUB_TOKEN")

# Initialize the Github object
g = Github(token)

# Get the repository object for the pull request
repo = g.get_repo(repo_url.split("/")[-2:])

# Get the pull request object
pull_request = repo.get_pull(pull_request_number)

# Get the diff for the pull request
diff_url = f"{repo_url}/compare/{base_branch}...{head_branch}.diff"
diff_response = requests.get(diff_url)

# Parse the diff and check for made-up lines
# Replace the following code with your fact-checking logic

made_up_lines = []
for line in diff_response.text.splitlines():
    if line.startswith("+") and "made up" in line:
        made_up_lines.append(line)

# Comment on the pull request with the list of made-up lines
if made_up_lines:
    try:
        pull_request.create_issue_comment(
            f"Found {len(made_up_lines)} made-up lines:\n" + "\n".join(made_up_lines)
        )
    except GithubException as e:
        print(e)