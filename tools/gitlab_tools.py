import gitlab
import os
from dotenv import load_dotenv

load_dotenv()

def get_gitlab_client():
    gl = gitlab.Gitlab(
        url=os.getenv("GITLAB_URL", "https://gitlab.com"),
        private_token=os.getenv("GITLAB_TOKEN")
    )
    gl.auth()
    return gl


def list_projects() -> dict:
    """List all GitLab projects owned by the authenticated user."""
    gl = get_gitlab_client()
    projects = gl.projects.list(owned=True, get_all=True)
    return {
        "projects": [
            {"id": p.id, "name": p.name, "description": p.description or ""}
            for p in projects
        ]
    }


def list_issues(project_id: int, state: str = "opened") -> dict:
    """
    List issues for a GitLab project.
    Args:
        project_id: The numeric GitLab project ID
        state: 'opened', 'closed', or 'all'
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issues = project.issues.list(state=state, get_all=True)
    return {
        "project": project.name,
        "issues": [
            {
                "id": i.iid,
                "title": i.title,
                "description": i.description or "",
                "labels": i.labels,
                "state": i.state,
                "created_at": i.created_at,
                "author": i.author.get("username", "unknown")
            }
            for i in issues
        ]
    }


def get_issue_detail(project_id: int, issue_iid: int) -> dict:
    """
    Get full detail of a single issue including comments.
    Args:
        project_id: The numeric GitLab project ID
        issue_iid: The issue number shown in GitLab UI
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issue = project.issues.get(issue_iid)
    notes = issue.notes.list(get_all=True)
    return {
        "id": issue.iid,
        "title": issue.title,
        "description": issue.description or "",
        "labels": issue.labels,
        "state": issue.state,
        "created_at": issue.created_at,
        "author": issue.author.get("username", "unknown"),
        "comments": [
            {"author": n.author.get("username"), "body": n.body}
            for n in notes if not n.system
        ]
    }


def list_pipelines(project_id: int, status: str = None) -> dict:
    """
    List CI/CD pipelines for a project.
    Args:
        project_id: The numeric GitLab project ID
        status: Optional filter - 'running', 'failed', 'success', 'canceled'
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    kwargs = {"get_all": False, "per_page": 10}
    if status:
        kwargs["status"] = status
    pipelines = project.pipelines.list(**kwargs)
    return {
        "project": project.name,
        "pipelines": [
            {
                "id": p.id,
                "status": p.status,
                "ref": p.ref,
                "created_at": p.created_at,
                "web_url": p.web_url
            }
            for p in pipelines
        ]
    }


def get_pipeline_jobs(project_id: int, pipeline_id: int) -> dict:
    """
    Get all jobs in a pipeline, including failure logs.
    Args:
        project_id: The numeric GitLab project ID
        pipeline_id: The numeric pipeline ID
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    pipeline = project.pipelines.get(pipeline_id)
    jobs = pipeline.jobs.list(get_all=True)
    result = []
    for job in jobs:
        job_data = {
            "id": job.id,
            "name": job.name,
            "stage": job.stage,
            "status": job.status,
        }
        if job.status == "failed":
            try:
                log = project.jobs.get(job.id).trace()
                log_text = log.decode("utf-8") if isinstance(log, bytes) else str(log)
                job_data["log_tail"] = log_text[-2000:]  # Last 2000 chars
            except Exception:
                job_data["log_tail"] = "Could not fetch log"
        result.append(job_data)
    return {"pipeline_id": pipeline_id, "jobs": result}


def get_project_summary(project_id: int) -> dict:
    """
    Get a high-level summary of a project for standup/retro use.
    Args:
        project_id: The numeric GitLab project ID
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    open_issues = project.issues.list(state="opened", get_all=True)
    closed_issues = project.issues.list(state="closed", per_page=10)
    mrs = project.mergerequests.list(state="opened", get_all=True)
    pipelines = project.pipelines.list(per_page=5)
    return {
        "project_name": project.name,
        "description": project.description or "",
        "open_issues_count": len(open_issues),
        "open_issues": [{"id": i.iid, "title": i.title, "labels": i.labels} 
                        for i in open_issues],
        "recent_closed_issues": [{"id": i.iid, "title": i.title} 
                                  for i in closed_issues],
        "open_merge_requests": [{"id": m.iid, "title": m.title, "author": m.author.get("username")} 
                                 for m in mrs],
        "recent_pipelines": [{"id": p.id, "status": p.status, "ref": p.ref} 
                              for p in pipelines]
    }

def list_merge_requests(project_id: int, state: str = "opened") -> dict:
    """
    List merge requests for a GitLab project.
    Args:
        project_id: The numeric GitLab project ID
        state: 'opened', 'closed', 'merged', or 'all'
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    mrs = project.mergerequests.list(state=state, get_all=True)
    return {
        "project": project.name,
        "merge_requests": [
            {
                "id": m.iid,
                "title": m.title,
                "author": m.author.get("username"),
                "state": m.state,
                "source_branch": m.source_branch,
                "target_branch": m.target_branch,
                "created_at": m.created_at,
                "web_url": m.web_url
            }
            for m in mrs
        ]
    }