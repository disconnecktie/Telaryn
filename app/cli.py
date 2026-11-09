"""Provide private local administration without exposing registration endpoints."""

import argparse
from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth import hash_password
from app.services.workspaces import get_or_create_bootstrap_workspace
from app.services.access_requests import purge_expired_requests
from app.services.feedback_retention import purge_closed_feedback


def set_password(email: str) -> None:
    with SessionLocal() as db:
        get_or_create_bootstrap_workspace(db)
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            raise SystemExit("No Telaryn user exists with that email.")
        first = getpass("New Telaryn password: ")
        second = getpass("Confirm Telaryn password: ")
        if first != second:
            raise SystemExit("Passwords did not match.")
        if len(first) < 12:
            raise SystemExit("Use at least 12 characters for the Telaryn password.")
        user.password_hash = hash_password(first)
        db.commit()
    print(f"Password updated for {email.strip().lower()}.")


def show_user_id(email: str) -> None:
    """Print one exact user's non-secret deployment identifier."""
    normalized_email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None:
            raise SystemExit("No Telaryn user exists with that email.")
        print(f"TELARYN_USER_ID={user.id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Private Telaryn administration")
    subparsers = parser.add_subparsers(dest="command", required=True)
    password_parser = subparsers.add_parser("set-password")
    password_parser.add_argument("email")
    user_id_parser = subparsers.add_parser(
        "show-user-id", help="Print one exact user's numeric deployment identifier."
    )
    user_id_parser.add_argument("email")
    subparsers.add_parser("purge-access-requests", help="Delete expired intake and lifecycle records.")
    subparsers.add_parser(
        "purge-retained-data",
        help="Apply approved access-request and closed-feedback retention policies.",
    )
    args = parser.parse_args()
    if args.command == "set-password":
        set_password(args.email)
    elif args.command == "show-user-id":
        show_user_id(args.email)
    elif args.command == "purge-access-requests":
        with SessionLocal() as db:
            count = purge_expired_requests(db)
            db.commit()
        print(f"Deleted {count} expired access requests and their history.")
    elif args.command == "purge-retained-data":
        with SessionLocal() as db:
            access_requests = purge_expired_requests(db)
            feedback = purge_closed_feedback(db)
            db.commit()
        print(
            "Retention cleanup complete: "
            f"access_requests={access_requests}, "
            f"feedback_screenshots={feedback.screenshots_purged}, "
            f"feedback_records={feedback.feedback_records_purged}."
        )


if __name__ == "__main__":
    main()
