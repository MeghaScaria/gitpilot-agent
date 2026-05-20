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

def get_pipeline_failure_diagnosis(project_id: int) -> dict:
    """
    Fetch the most recent failed pipeline, get its job logs,
    and return structured data for diagnosis.
    Args:
        project_id: The numeric GitLab project ID
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    failed = project.pipelines.list(status="failed", per_page=1)
    if not failed:
        return {"message": "No failed pipelines found."}
    pipeline = failed[0]
    jobs = project.pipelines.get(pipeline.id).jobs.list(get_all=True)
    job_logs = []
    for job in jobs:
        if job.status == "failed":
            try:
                log = project.jobs.get(job.id).trace()
                log_text = log.decode("utf-8") if isinstance(log, bytes) else str(log)
                job_logs.append({
                    "job_name": job.name,
                    "stage": job.stage,
                    "log_tail": log_text[-3000:]
                })
            except Exception as e:
                job_logs.append({
                    "job_name": job.name,
                    "stage": job.stage,
                    "log_tail": f"Could not fetch log: {e}"
                })
    return {
        "pipeline_id": pipeline.id,
        "ref": pipeline.ref,
        "created_at": pipeline.created_at,
        "web_url": pipeline.web_url,
        "failed_jobs": job_logs
    }


def generate_mr_description(project_id: int, mr_iid: int) -> dict:
    """
    Fetch the diff and metadata for a merge request to help
    generate a professional MR description.
    Args:
        project_id: The numeric GitLab project ID
        mr_iid: The merge request IID shown in GitLab UI
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    mr = project.mergerequests.get(mr_iid)
    try:
        changes = mr.changes()
        diffs = changes.get("changes", [])
        diff_summary = []
        for d in diffs[:10]:  # Limit to first 10 files
            diff_summary.append({
                "file": d.get("new_path", ""),
                "additions": d.get("diff", "").count("\n+"),
                "deletions": d.get("diff", "").count("\n-"),
                "diff_snippet": d.get("diff", "")[:800]
            })
    except Exception as e:
        diff_summary = [{"error": str(e)}]
    return {
        "mr_id": mr.iid,
        "title": mr.title,
        "source_branch": mr.source_branch,
        "target_branch": mr.target_branch,
        "author": mr.author.get("username"),
        "created_at": mr.created_at,
        "existing_description": mr.description or "",
        "file_changes": diff_summary
    }


def generate_sprint_retrospective(project_id: int) -> dict:
    """
    Gather recent project activity to generate a sprint retrospective.
    Includes recently closed issues, merged MRs, failed pipelines, and open items.
    Args:
        project_id: The numeric GitLab project ID
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    closed_issues = project.issues.list(state="closed", per_page=10,
                                         order_by="updated_at")
    open_issues = project.issues.list(state="opened", get_all=True)
    merged_mrs = project.mergerequests.list(state="merged", per_page=10,
                                             order_by="updated_at")
    open_mrs = project.mergerequests.list(state="opened", get_all=True)
    pipelines = project.pipelines.list(per_page=10)
    pipeline_summary = {
        "total": len(pipelines),
        "failed": len([p for p in pipelines if p.status == "failed"]),
        "success": len([p for p in pipelines if p.status == "success"])
    }
    return {
        "project_name": project.name,
        "recently_closed_issues": [
            {"id": i.iid, "title": i.title, "labels": i.labels}
            for i in closed_issues
        ],
        "open_issues": [
            {"id": i.iid, "title": i.title, "labels": i.labels}
            for i in open_issues
        ],
        "merged_mrs": [
            {"id": m.iid, "title": m.title, "author": m.author.get("username")}
            for m in merged_mrs
        ],
        "open_mrs": [
            {"id": m.iid, "title": m.title}
            for m in open_mrs
        ],
        "pipeline_health": pipeline_summary
    }

def create_issue_comment(project_id: int, issue_iid: int, comment: str) -> dict:
    """
    Post a comment on a GitLab issue.
    Args:
        project_id: The numeric GitLab project ID
        issue_iid: The issue number shown in GitLab UI
        comment: The comment text to post
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issue = project.issues.get(issue_iid)
    note = issue.notes.create({"body": comment})
    return {
        "success": True,
        "issue_id": issue_iid,
        "comment_id": note.id,
        "comment": comment
    }


def update_issue_labels(project_id: int, issue_iid: int, labels: list) -> dict:
    """
    Update the labels on a GitLab issue.
    Args:
        project_id: The numeric GitLab project ID
        issue_iid: The issue number shown in GitLab UI
        labels: List of label strings to apply e.g. ["bug", "high-priority"]
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issue = project.issues.get(issue_iid)
    issue.labels = labels
    issue.save()
    return {
        "success": True,
        "issue_id": issue_iid,
        "labels_applied": labels
    }


def close_issue(project_id: int, issue_iid: int) -> dict:
    """
    Close a GitLab issue.
    Args:
        project_id: The numeric GitLab project ID
        issue_iid: The issue number shown in GitLab UI
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    issue = project.issues.get(issue_iid)
    issue.state_event = "close"
    issue.save()
    return {
        "success": True,
        "issue_id": issue_iid,
        "message": f"Issue #{issue_iid} has been closed."
    }


def create_mr_comment(project_id: int, mr_iid: int, comment: str) -> dict:
    """
    Post a comment on a GitLab merge request.
    Args:
        project_id: The numeric GitLab project ID
        mr_iid: The merge request IID shown in GitLab UI
        comment: The comment text to post
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    mr = project.mergerequests.get(mr_iid)
    note = mr.notes.create({"body": comment})
    return {
        "success": True,
        "mr_id": mr_iid,
        "comment_id": note.id,
        "comment": comment
    }
def create_issue(project_id: int, title: str, description: str, labels: list = None) -> dict:
    """
    Create a new issue in a GitLab project.
    Args:
        project_id: The numeric GitLab project ID
        title: The issue title
        description: The issue description (markdown supported)
        labels: Optional list of label strings e.g. ["bug", "pipeline-failure"]
    """
    gl = get_gitlab_client()
    project = gl.projects.get(project_id)
    payload = {
        "title": title,
        "description": description,
        "labels": ",".join(labels) if labels else ""
    }
    issue = project.issues.create(payload)
    return {
        "success": True,
        "issue_id": issue.iid,
        "title": issue.title,
        "url": issue.web_url,
        "labels": labels or []
    }