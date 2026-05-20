from agent.core import run_agent

print("🚀 GitPilot Agent Test\n")
print("=" * 50)

# Test 1: List projects
print("\n📋 Test 1: List my projects")
response = run_agent("What GitLab projects do I have access to?")
print(response)

print("\n" + "=" * 50)

# Test 2: Prioritize issues (the money demo feature)
print("\n🎯 Test 2: Prioritize issues")
response = run_agent(
    "Look at the open issues in my demo-app project and "
    "tell me which ones I should fix first, ranked by priority. "
    "Explain your reasoning."
)
print(response)