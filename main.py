"""Console entry point for the Smart Complaint Management System."""

from __future__ import annotations

from collections.abc import Callable

from db import ComplaintDatabase
from models import Category, Complaint
from services.complaint_service import ComplaintService

CATEGORIES: tuple[Category, ...] = (
    "electrical",
    "plumbing",
    "academic",
    "hostel",
    "other",
)


def prompt_non_empty(label: str) -> str:
    while True:
        value = input(label).strip()
        if value:
            return value
        print("This field cannot be empty.")


def prompt_int(label: str, minimum: int, maximum: int) -> int:
    while True:
        try:
            value = int(input(label).strip())
            if minimum <= value <= maximum:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number from {minimum} to {maximum}.")


def prompt_category() -> Category:
    print("Categories: " + ", ".join(CATEGORIES))
    while True:
        value = input("Category: ").strip().lower()
        if value in CATEGORIES:
            return value  # type: ignore[return-value]
        print("Choose one of the listed categories.")


def print_complaint(complaint: Complaint) -> None:
    print(
        f"[{complaint.id}] {complaint.title} | {complaint.category} | "
        f"priority={complaint.priority_score:.2f} | {complaint.status} | "
        f"raised by {complaint.raised_by} | level={complaint.escalation_level}"
    )
    print(f"    {complaint.description}")


def raise_new_complaint(service: ComplaintService) -> None:
    title = prompt_non_empty("Title: ")
    description = prompt_non_empty("Description: ")
    category = prompt_category()
    raised_by = prompt_non_empty("Raised by: ")
    urgency = prompt_int("Urgency (1-5): ", 1, 5)
    try:
        complaint = service.raise_complaint(
            title, description, category, raised_by, urgency
        )
    except ValueError as error:
        print(f"Could not raise complaint: {error}")
        return
    print(f"Complaint #{complaint.id} created with priority {complaint.priority_score:.2f}.")


def view_all(service: ComplaintService) -> None:
    complaints = service.all_by_priority()
    if not complaints:
        print("No complaints found.")
        return
    for complaint in complaints:
        print_complaint(complaint)


def resolve_next(service: ComplaintService) -> None:
    complaint = service.resolve_next()
    if complaint is None:
        print("The processing queue is empty.")
        return
    print(f"Resolved complaint #{complaint.id}: {complaint.title}")


def search_complaints(service: ComplaintService) -> None:
    choice = input("Search by (i)d or (c)ategory: ").strip().lower()
    if choice == "i":
        complaint_id = prompt_int("Complaint id: ", 1, 2**31 - 1)
        complaint = service.search_by_id(complaint_id)
        print_complaint(complaint) if complaint else print("Complaint not found.")
    elif choice == "c":
        category = prompt_category()
        complaints = service.search_by_category(category)
        if not complaints:
            print("No complaints in that category.")
        for complaint in complaints:
            print_complaint(complaint)
    else:
        print("Choose i or c.")


def escalation_menu(service: ComplaintService) -> None:
    choice = input("(v)iew status, (a)dvance time, or (c)heck escalation: ").strip().lower()
    if choice == "v":
        complaints = [
            complaint
            for complaint in service.by_id.values()
            if complaint.status != "resolved"
        ]
        if not complaints:
            print("No unresolved complaints.")
        for complaint in sorted(complaints, key=lambda item: item.id or 0):
            print(
                f"Complaint #{complaint.id}: {complaint.status}, "
                f"level {complaint.escalation_level} "
                f"({service.escalation_target(complaint.escalation_level)})"
            )
    elif choice == "a":
        while True:
            try:
                hours = float(input("Advance simulated hours: "))
                service.advance_time(hours)
                print(f"Simulated clock is now {hours:g} hours ahead.")
                break
            except ValueError as error:
                print(f"Invalid time: {error}")
    elif choice == "c":
        escalated = service.force_escalation_check()
        if not escalated:
            print("No complaints require escalation.")
        for complaint in escalated:
            print(
                f"Complaint #{complaint.id} escalated to "
                f"{service.escalation_target(complaint.escalation_level)}."
            )
    else:
        print("Choose a or c.")


def audit_menu(service: ComplaintService) -> None:
    complaint_id = prompt_int("Complaint id: ", 1, 2**31 - 1)
    if service.search_by_id(complaint_id) is None:
        print("Complaint not found.")
        return
    trail = service.audit_trail(complaint_id)
    if not trail:
        print("No audit entries.")
        return
    for change in trail:
        print(
            f"{change.changed_at:%Y-%m-%d %H:%M:%S}: "
            f"{change.old_status} -> {change.new_status} ({change.note})"
        )


def show_stats(service: ComplaintService) -> None:
    stats = service.stats()
    print("By category:", stats["by_category"])
    print("By status:", stats["by_status"])
    print(f"Average resolution time: {stats['average_resolution_hours']:.2f} hours")


def print_menu() -> None:
    print(
        "\nSmart Complaint Management System\n"
        "1. Raise a new complaint\n"
        "2. View all complaints\n"
        "3. Resolve next complaint\n"
        "4. Search complaint by ID or category\n"
        "5. View escalation status / force escalation check\n"
        "6. View audit trail\n"
        "7. View simple stats\n"
        "8. Exit"
    )


def run() -> None:
    database = ComplaintDatabase()
    service = ComplaintService(database)
    actions: dict[str, Callable[[], None]] = {
        "1": lambda: raise_new_complaint(service),
        "2": lambda: view_all(service),
        "3": lambda: resolve_next(service),
        "4": lambda: search_complaints(service),
        "5": lambda: escalation_menu(service),
        "6": lambda: audit_menu(service),
        "7": lambda: show_stats(service),
    }
    try:
        while True:
            print_menu()
            choice = input("Choose an option: ").strip()
            if choice == "8":
                print("Goodbye.")
                break
            action = actions.get(choice)
            if action:
                action()
            else:
                print("Choose a number from 1 to 8.")
    finally:
        database.close()


if __name__ == "__main__":
    run()
