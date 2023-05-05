import os
import sys
import requests
from github import Github, GithubException
import subprocess

# Get the arguments passed to the script
repo_url = sys.argv[1]
head_branch = sys.argv[2]
base_branch = sys.argv[3]
pull_request_number = int(sys.argv[4])

# Get the authentication token from the environment variable
token = os.environ.get("GITHUB_TOKEN")

# Initialize the Github object
g = Github(token)

repo_name = "/".join(repo_url.split("/")[-2:]).replace(".git", "")

# Get the repository object for the pull request
repo = g.get_repo(repo_name)

# Get the pull request object
pull_request = repo.get_pull(pull_request_number)

# Get the diff for the pull request
#diff_url = f"{repo_url}/compare/{base_branch}...{head_branch}.diff"
#diff_response = requests.get(diff_url)

# Get the repository path on the runner
repo_path = os.environ['GITHUB_WORKSPACE']
print('repo_path', repo_path)

# Check out the base branch and head branch
print('git1', subprocess.run(['git', 'checkout', base_branch], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False))
print('git2', subprocess.run(['git', 'checkout', head_branch], cwd=repo_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False))

# Get the diff for the pull request
diff_output = subprocess.check_output(['git', 'diff', '--no-prefix', '--unified=0', base_branch, head_branch], cwd=repo_path)

# Convert the bytes to a string
diff_str = diff_output.decode('utf-8')

# Print the diff
print(diff_str)


# Parse the diff and check for made-up lines
# Replace the following code with your fact-checking logic

made_up_lines = []
for line in diff_str.splitlines():
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