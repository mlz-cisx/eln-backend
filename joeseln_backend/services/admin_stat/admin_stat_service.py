import os
import subprocess

from sqlalchemy.orm import Session

from joeseln_backend.conf.base_conf import FILES_BASE_PATH, PICTURES_BASE_PATH
from joeseln_backend.models import models
from joeseln_backend.services.admin_stat.admin_stat_schemas import StatResponse


def get_directory_size(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            total_size += os.path.getsize(filepath)
    return total_size


def get_git_commit_info():
    backend_path = os.path.dirname(os.path.abspath(__file__))
    try:
        commit_hash = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=backend_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        commit_msg = subprocess.run(
            ['git', 'log', '-1', '--format=%s'],
            cwd=backend_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        return commit_hash, commit_msg
    except (OSError, subprocess.SubprocessError):
        return None, None


def get_stat(db: Session, user):
    if not user.admin:
        return None

    total_users = db.query(models.User).count()

    active_users = db.query(models.UserConnectedWs).filter_by(connected=True).count()

    total_labbook = db.query(models.Labbook).count()
    total_notes = db.query(models.Note).count()
    total_files = db.query(models.File).count()
    total_pics = db.query(models.Picture).count()

    image_folder_size = get_directory_size(PICTURES_BASE_PATH)
    files_folder_size = get_directory_size(FILES_BASE_PATH)

    git_commit_hash, git_commit_msg = get_git_commit_info()

    return StatResponse(
        total_users=total_users,
        active_users=active_users,
        total_labbook=total_labbook,
        total_notes=total_notes,
        total_files=total_files,
        total_pics=total_pics,
        image_folder_size=image_folder_size,
        files_folder_size=files_folder_size,
        git_commit_hash=git_commit_hash,
        git_commit_msg=git_commit_msg,
    )
